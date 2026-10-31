using System;
using System.IO;
using System.Net.Sockets;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Threading;

// Headless Vintage Story bot client for the benchmark. Speaks just enough of the game protocol to count as an
// online player: identification, request-join, client-loaded, client-playing, ping replies, positions over TCP.
// It never moves and never sends anything else. Needs VerifyPlayerAuth=false on the server (no master-server auth).
// Uses the server's own packet classes and serializers from VintagestoryLib.dll (resolved from $VS_SERVER at runtime).
internal static class Program
{
    static string host = "127.0.0.1", name = "SUHBenchBot"; static int port = 42420, view = 128, retrySec = 120; static bool verbose;

    static int Main(string[] args)
    {
        for (int i = 0; i < args.Length; i++)
        {
            switch (args[i])
            {
                case "--host": host = args[++i]; break;
                case "--port": port = int.Parse(args[++i]); break;
                case "--name": name = args[++i]; break;
                case "--view": view = int.Parse(args[++i]); break;
                case "--retry": retrySec = int.Parse(args[++i]); break;
                case "--verbose": verbose = true; break;
            }
        }
        var vs = Environment.GetEnvironmentVariable("VS_SERVER") ?? AppContext.BaseDirectory;
        AppDomain.CurrentDomain.AssemblyResolve += (s, e) =>
        {
            var n = new AssemblyName(e.Name).Name;
            foreach (var dir in new[] { vs, Path.Combine(vs, "Lib") })
            {
                var p = Path.Combine(dir, n + ".dll");
                if (File.Exists(p)) return Assembly.LoadFrom(p);
            }
            return null;
        };
        try { return Run(); }
        catch (Exception e) { Log("FATAL " + e); return 3; }
    }

    static void Log(string s) { Console.WriteLine($"[{DateTime.Now:HH:mm:ss}] [VSBot] {s}"); Console.Out.Flush(); }

    [MethodImpl(MethodImplOptions.NoInlining)]
    static int Run()
    {
        string uid = "suhbot-" + name.ToLowerInvariant();
        TcpClient tcp = null; var t0 = DateTime.UtcNow;
        while (tcp == null)
        {
            try { tcp = new TcpClient(); tcp.Connect(host, port); }
            catch (Exception) { tcp = null; if ((DateTime.UtcNow - t0).TotalSeconds > retrySec) { Log($"could not connect to {host}:{port} within {retrySec} s"); return 2; } Thread.Sleep(1000); }
        }
        tcp.NoDelay = true;
        var stream = tcp.GetStream();
        Log($"connected to {host}:{port}; identifying as {name} (uid {uid}), network version {Vintagestory.API.Config.GameVersion.NetworkVersion}, game {Vintagestory.API.Config.GameVersion.ShortGameVersion}");
        Send(stream, new Packet_Client
        {
            Id = 1,
            Identification = new Packet_ClientIdentification
            {
                Playername = name, PlayerUID = uid, MpToken = "", ServerPassword = null,
                MdProtocolVersion = Vintagestory.API.Config.GameVersion.ShortGameVersion,
                NetworkVersion = Vintagestory.API.Config.GameVersion.NetworkVersion,
                ShortGameVersion = Vintagestory.API.Config.GameVersion.ShortGameVersion,
                ViewDistance = view, RenderMetaBlocks = 0,
            }
        });
        bool joined = false, spawned = false; long packets = 0, bytes = 0, pings = 0; var lastStat = DateTime.UtcNow;
        var head = new byte[4];
        while (true)
        {
            if (!ReadExactly(stream, head, 4)) { Log($"server closed the connection ({packets} packets, {bytes / 1024} KB received, {pings} pings answered)"); return 0; }
            int raw = (head[0] << 24) | (head[1] << 16) | (head[2] << 8) | head[3];
            bool compressed = (raw & int.MinValue) != 0; int len = raw & 0x7FFFFFFF;
            var payload = new byte[len];
            if (!ReadExactly(stream, payload, len)) { Log("connection dropped mid-packet"); return 0; }
            packets++; bytes += len + 4;
            if (compressed) payload = Vintagestory.Common.Compression.Decompress(payload);
            var p = Packet_ServerSerializer.DeserializeBuffer(payload, payload.Length, new Packet_Server());
            switch (p.Id)
            {
                case 1: Log("server identification received"); break;
                case 73: // ServerReady: the real client finishes loading assets here, then asks to join
                    if (!joined) { joined = true; Log("server ready, requesting join"); Send(stream, new Packet_Client { Id = 11, RequestJoin = new Packet_ClientRequestJoin { Language = "en" } }); }
                    break;
                case 41: // PlayerData for ourselves: the real client sends ClientLoaded here, then ClientPlaying once its systems are ready
                    if (!spawned && p.PlayerData != null && p.PlayerData.PlayerUID == uid)
                    {
                        spawned = true;
                        Log($"own player data received (entity {p.PlayerData.EntityId}, spawn {p.PlayerData.Spawnx},{p.PlayerData.Spawny},{p.PlayerData.Spawnz}); sending ClientLoaded, ClientPlaying, positions over TCP");
                        Send(stream, new Packet_Client { Id = 26 });
                        Send(stream, new Packet_Client { Id = 29 });
                        Send(stream, new Packet_Client { Id = 34 });
                    }
                    break;
                case 6: Log("level finalize received"); break;
                case 2: pings++; Send(stream, new Packet_Client { Id = 2, PingReply = new Packet_ClientPingReply() }); break;
                case 9: Log("disconnected by server: " + p.DisconnectPlayer?.DisconnectReason); return 2;
                default: if (verbose) Log($"packet id {p.Id} ({len} bytes)"); break;
            }
            if ((DateTime.UtcNow - lastStat).TotalSeconds >= 60) { lastStat = DateTime.UtcNow; Log($"alive: {packets} packets, {bytes / 1024} KB received, {pings} pings answered, playing={spawned}"); }
        }
    }

    static void Send(NetworkStream s, Packet_Client p)
    {
        var data = Packet_ClientSerializer.SerializeToBytes(p);
        var buf = new byte[data.Length + 4];
        buf[0] = (byte)(data.Length >> 24); buf[1] = (byte)(data.Length >> 16); buf[2] = (byte)(data.Length >> 8); buf[3] = (byte)data.Length;
        Buffer.BlockCopy(data, 0, buf, 4, data.Length);
        lock (s) { s.Write(buf, 0, buf.Length); s.Flush(); }
    }

    static bool ReadExactly(NetworkStream s, byte[] buf, int len)
    {
        int got = 0;
        while (got < len) { int n; try { n = s.Read(buf, got, len - got); } catch (IOException) { return false; } if (n <= 0) return false; got += n; }
        return true;
    }
}
