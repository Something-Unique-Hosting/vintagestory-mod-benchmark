using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using HarmonyLib;
using Vintagestory.API.Common;
using Vintagestory.API.Common.Entities;
using Vintagestory.API.MathTools;
using Vintagestory.API.Server;

namespace SuhBench
{
    // Headless, player-free server benchmark for comparing mod sets on the same server build. Phases:
    //   1. worldgen  - request a square of chunk columns around spawn, time until all are loaded
    //   2. settle    - let background chunk work finish (not reported)
    //   3. idle      - steady state with those chunks kept loaded
    //   4. entities  - spawn N always-active creatures, measure tick cost (or a ladder of spawn steps)
    // Every main-thread tick is timed with a Harmony hook around ServerMain.Process/ProcessMain.
    // Mod-benchmark extras: the loaded mod list, server run-phase timestamps (where startup time goes),
    // and per-mod attribution of game-tick listeners and entity behaviours. One JSON file, then shutdown.
    public class BenchModSystem : ModSystem
    {
        static readonly double TicksToMs = 1000.0 / Stopwatch.Frequency;

        string label, mode, outPath;
        int radius, idleSec, settleSec, entityCount, entitySec;
        int[] ladder = Array.Empty<int>(); int stepSec, spawnPerTick; double ladderStopMs;
        int ladderIdx = -1, spawnQueue; bool spawning;
        readonly List<Dictionary<string, object>> ladderResults = new List<Dictionary<string, object>>();
        internal static volatile int LadderStep = 0;

        ICoreServerAPI sapi;
        Harmony harmony;
        Process proc;

        internal static volatile int Phase = 0; // 0 none, 1 worldgen, 2 settle, 3 idle, 4 entities, 5 done
        internal static readonly Stopwatch Clock = Stopwatch.StartNew();
        internal static readonly List<double[]> TickSeries = new List<double[]>();
        internal static readonly Dictionary<int, List<double>> PhaseTicks = new Dictionary<int, List<double>>();
        [ThreadStatic] static long tickStart;
        [ThreadStatic] static bool armed;

        readonly List<Dictionary<string, object>> samples = new List<Dictionary<string, object>>();
        readonly Dictionary<string, object> result = new Dictionary<string, object>();
        readonly Dictionary<string, double> runPhases = new Dictionary<string, double>();
        int totalColumns, loadedColumns;
        double phaseStartMs, startupMs, startupClockMs;
        TimeSpan phaseStartCpu;
        long phaseStartGcPause;
        int[] phaseStartGc = new int[3];
        long tickListenerId;
        int spawnedEntities;
        List<string> spawnedCodes = new List<string>();
        double phaseDeadlineMs;

        public override bool ShouldLoad(EnumAppSide side) => side == EnumAppSide.Server;
        public override double ExecuteOrder() => 0.05;

        public override void StartServerSide(ICoreServerAPI api)
        {
            sapi = api;
            proc = Process.GetCurrentProcess();
            label = Env("BENCH_LABEL", "unknown");
            mode = Env("BENCH_MODE", "gen");
            outPath = Env("BENCH_OUT", Path.Combine(api.DataBasePath, "bench-result.json"));
            radius = int.Parse(Env("BENCH_RADIUS", "16"));
            idleSec = int.Parse(Env("BENCH_IDLE_SEC", "20"));
            settleSec = int.Parse(Env("BENCH_SETTLE_SEC", "20"));
            entityCount = int.Parse(Env("BENCH_ENTITIES", "300"));
            entitySec = int.Parse(Env("BENCH_ENTITY_SEC", "45"));
            var lad = Env("BENCH_LADDER", "");
            if (lad.Length > 0) ladder = lad.Split(',').Select(s => int.Parse(s.Trim())).ToArray();
            stepSec = int.Parse(Env("BENCH_STEP_SEC", "30"));
            spawnPerTick = int.Parse(Env("BENCH_SPAWN_PER_TICK", "250"));
            ladderStopMs = double.Parse(Env("BENCH_LADDER_STOP_MS", "150"), System.Globalization.CultureInfo.InvariantCulture);

            for (int p = 1; p <= 4; p++) PhaseTicks[p] = new List<double>();

            harmony = new Harmony("suh.bench");
            var serverMain = AccessTools.TypeByName("Vintagestory.Server.ServerMain");
            harmony.Patch(AccessTools.Method(serverMain, "Process"), prefix: new HarmonyMethod(AccessTools.Method(typeof(BenchModSystem), nameof(ProcessPrefix))));
            harmony.Patch(AccessTools.Method(serverMain, "ProcessMain"), postfix: new HarmonyMethod(AccessTools.Method(typeof(BenchModSystem), nameof(ProcessMainPostfix))));

            if (Env("BENCH_SYSTIMING", "0") == "1") { try { PatchSystemTimings(serverMain.Assembly); } catch (Exception e) { api.Logger.Warning("[SuhBench] system timing disabled: {0}", e.Message); } }
            if (Env("BENCH_MODTIMING", "1") == "1") { try { PatchModTimings(serverMain.Assembly); } catch (Exception e) { api.Logger.Warning("[SuhBench] mod timing disabled: {0}", e.Message); } }

            // run-phase timestamps: where the startup time goes (asset loading, world load, ...)
            foreach (EnumServerRunPhase ph in Enum.GetValues(typeof(EnumServerRunPhase)))
            {
                if (ph == EnumServerRunPhase.Exit || ph == EnumServerRunPhase.Shutdown || ph == EnumServerRunPhase.Standby) continue;
                var name = ph.ToString();
                try { api.Event.ServerRunPhase(ph, () => { if (!runPhases.ContainsKey(name)) runPhases[name] = (DateTime.Now - proc.StartTime).TotalMilliseconds; }); } catch { }
            }
            runPhases["BenchModStarted"] = (DateTime.Now - proc.StartTime).TotalMilliseconds;
            api.Event.ServerRunPhase(EnumServerRunPhase.RunGame, OnRunGame);
            api.Logger.Notification("[SuhBench] armed: label={0} mode={1} radius={2} entities={3} ladder={4}", label, mode, radius, entityCount, lad);
        }

        // ---- optional per-ServerSystem timing (diagnostic) ----
        internal static readonly Dictionary<int, Dictionary<string, double[]>> SysTime = new Dictionary<int, Dictionary<string, double[]>>();
        [ThreadStatic] static long sysStart;
        void PatchSystemTimings(Assembly lib)
        {
            for (int p = 1; p <= 4; p++) SysTime[p] = new Dictionary<string, double[]>();
            var baseType = lib.GetType("Vintagestory.Server.ServerSystem");
            var pre = new HarmonyMethod(AccessTools.Method(typeof(BenchModSystem), nameof(SysPrefix)));
            var post = new HarmonyMethod(AccessTools.Method(typeof(BenchModSystem), nameof(SysPostfix)));
            int n = 0;
            foreach (var t in SafeTypes(lib))
            {
                if (t.IsAbstract || !baseType.IsAssignableFrom(t) || t == baseType) continue;
                var m = t.GetMethod("OnServerTick", BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly);
                if (m == null) continue;
                try { harmony.Patch(m, prefix: pre, postfix: post); n++; } catch (Exception e) { sapi.Logger.Warning("[SuhBench] could not patch {0}: {1}", t.Name, e.Message); }
            }
            var em = lib.GetType("Vintagestory.Server.ServerEventManager");
            foreach (var name in new[] { "TriggerGameTick", "TriggerGameTickDebug" })
            {
                try
                {
                    var m = em?.GetMethod(name, BindingFlags.Public | BindingFlags.Instance);
                    if (m != null && m.DeclaringType != m.ReflectedType) m = m.DeclaringType.GetMethod(name, BindingFlags.Public | BindingFlags.Instance);
                    if (m != null) { harmony.Patch(m, prefix: pre, postfix: post); n++; }
                }
                catch (Exception e) { sapi.Logger.Warning("[SuhBench] could not patch {0}: {1}", name, e.Message); }
            }
            try
            {
                var pm = lib.GetType("Vintagestory.Server.ServerMain").GetMethod("ProcessMainThreadTasks");
                if (pm != null) { harmony.Patch(pm, prefix: pre, postfix: post); n++; }
            }
            catch (Exception e) { sapi.Logger.Warning("[SuhBench] could not patch ProcessMainThreadTasks: {0}", e.Message); }
            sapi.Logger.Notification("[SuhBench] system timing enabled on {0} methods", n);
        }
        static IEnumerable<Type> SafeTypes(Assembly a)
        {
            try { return a.GetTypes(); }
            catch (ReflectionTypeLoadException e) { return e.Types.Where(t => t != null); } // client-only types fail to load on Linux
        }
        public static void SysPrefix() { sysStart = Stopwatch.GetTimestamp(); }
        public static void SysPostfix(MethodBase __originalMethod)
        {
            int p = Phase; if (p < 1 || p > 4) return;
            double ms = (Stopwatch.GetTimestamp() - sysStart) * TicksToMs;
            string key = __originalMethod.DeclaringType.Name + "." + __originalMethod.Name;
            var d = SysTime[p];
            if (!d.TryGetValue(key, out var acc)) d[key] = acc = new double[3];
            acc[0] += ms; acc[1] += 1; if (ms > acc[2]) acc[2] = ms;
        }

        // ---- per-mod timing: game-tick listeners (incl. block entities) and entity behaviours declared by mods ----
        // Attribution is by the assembly that declared the handler/behaviour type, mapped to a mod id through the
        // mod loader. Handlers from the game's own assemblies land under "game". Work a mod does through Harmony
        // patches of game code, or through JSON-only content (recipes, patched entities), is NOT attributed here;
        // it shows up only in the per-system and whole-tick numbers.
        internal static readonly Dictionary<int, Dictionary<string, double[]>> ModTime = new Dictionary<int, Dictionary<string, double[]>>();
        static readonly Dictionary<Assembly, string> AsmToMod = new Dictionary<Assembly, string>();
        internal static readonly Dictionary<int, Dictionary<string, double[]>> ListenerTypes = new Dictionary<int, Dictionary<string, double[]>>();
        [ThreadStatic] static long modStart;
        [ThreadStatic] static int modDepth;
        void PatchModTimings(Assembly lib)
        {
            for (int p = 1; p <= 4; p++) { ModTime[p] = new Dictionary<string, double[]>(); ListenerTypes[p] = new Dictionary<string, double[]>(); }
            int n = 0;
            var lpre = new HarmonyMethod(AccessTools.Method(typeof(BenchModSystem), nameof(ListenerPrefix)));
            var lpost = new HarmonyMethod(AccessTools.Method(typeof(BenchModSystem), nameof(ListenerPostfix)));
            foreach (var tn in new[] { "Vintagestory.Common.GameTickListener", "Vintagestory.Common.GameTickListenerBlock" })
            {
                var t = lib.GetType(tn); if (t == null) continue;
                var m = t.GetMethod("OnTriggered", BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly);
                var f = t.GetField("Handler", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                if (m == null || f == null) { sapi.Logger.Warning("[SuhBench] {0}: OnTriggered/Handler not found, skipped", tn); continue; }
                try { harmony.Patch(m, prefix: lpre, postfix: lpost); n++; } catch (Exception e) { sapi.Logger.Warning("[SuhBench] could not patch {0}: {1}", tn, e.Message); }
            }
            sapi.Logger.Notification("[SuhBench] mod timing: {0} listener classes patched", n);
        }
        void PatchModBehaviours()
        {
            // called at RunGame, once every mod assembly is loaded
            var bpre = new HarmonyMethod(AccessTools.Method(typeof(BenchModSystem), nameof(BehaviourPrefix)));
            var bpost = new HarmonyMethod(AccessTools.Method(typeof(BenchModSystem), nameof(BehaviourPostfix)));
            int n = 0, seen = 0;
            foreach (var kv in AsmToMod.ToArray())
            {
                if (kv.Value == "game" || kv.Value == "suhbench") continue;
                foreach (var t in SafeTypes(kv.Key))
                {
                    if (t.IsAbstract || !typeof(EntityBehavior).IsAssignableFrom(t)) continue;
                    seen++;
                    var m = t.GetMethod("OnGameTick", BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly, null, new[] { typeof(float) }, null);
                    if (m == null || m.IsAbstract) continue;
                    try { harmony.Patch(m, prefix: bpre, postfix: bpost); n++; } catch (Exception e) { sapi.Logger.Warning("[SuhBench] could not patch behaviour {0}: {1}", t.Name, e.Message); }
                }
            }
            sapi.Logger.Notification("[SuhBench] mod timing: {0} mod entity behaviours patched ({1} behaviour types seen in mod assemblies); assemblies mapped: {2}", n, seen,
                string.Join(", ", AsmToMod.Where(kv => kv.Value != "game").Select(kv => kv.Key.GetName().Name + "->" + kv.Value)));
        }
        static string ModOf(Assembly a)
        {
            if (a == null) return "game";
            return AsmToMod.TryGetValue(a, out var id) ? id : "game";
        }
        static void Account(string mod, double ms)
        {
            int p = Phase; if (p < 1 || p > 4) return;
            var d = ModTime[p];
            if (!d.TryGetValue(mod, out var acc)) d[mod] = acc = new double[3];
            acc[0] += ms; acc[1] += 1; if (ms > acc[2]) acc[2] = ms;
        }
        public static void ListenerPrefix() { if (modDepth++ == 0) modStart = Stopwatch.GetTimestamp(); }
        static readonly Dictionary<Type, FieldInfo[]> HandlerFields = new Dictionary<Type, FieldInfo[]>();
        static FieldInfo[] HandlersOf(Type t)
        {
            // listener classes carry one or more delegate fields (GameTickListenerBlock has Handler and HandlerBare; only one is
            // set) and the runtime type may be a subclass of the patched class: collect every delegate field once per type
            lock (HandlerFields)
            {
                if (HandlerFields.TryGetValue(t, out var fs)) return fs;
                var list = new List<FieldInfo>();
                for (var b = t; b != null; b = b.BaseType)
                    foreach (var x in b.GetFields(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.DeclaredOnly))
                        if (typeof(Delegate).IsAssignableFrom(x.FieldType) && x.Name != "ErrorHandler") list.Add(x);
                HandlerFields[t] = fs = list.ToArray(); return fs;
            }
        }
        public static void ListenerPostfix(object __instance)
        {
            if (--modDepth != 0) return; // nested listener trigger: outer one owns the time
            double ms = (Stopwatch.GetTimestamp() - modStart) * TicksToMs;
            string mod = "game", tname = "?" + __instance.GetType().Name;
            try
            {
                Delegate h = null;
                foreach (var f in HandlersOf(__instance.GetType())) { h = f.GetValue(__instance) as Delegate; if (h != null) break; }
                if (h != null)
                {
                    var tt = h.Target?.GetType() ?? h.Method.DeclaringType;
                    mod = ModOf(tt?.Assembly);
                    if (mod == "game" && h.Method.DeclaringType != null) mod = ModOf(h.Method.DeclaringType.Assembly);
                    tname = (tt?.Assembly.GetName().Name ?? "?") + ":" + (tt?.FullName ?? "?");
                }
            }
            catch { }
            Account(mod + "/listeners", ms);
            int p = Phase;
            if (p >= 1 && p <= 4)
            {
                var d = ListenerTypes[p];
                if (!d.TryGetValue(tname, out var acc)) d[tname] = acc = new double[3];
                acc[0] += ms; acc[1] += 1; if (ms > acc[2]) acc[2] = ms;
            }
        }
        public static void BehaviourPrefix() { if (modDepth++ == 0) modStart = Stopwatch.GetTimestamp(); }
        public static void BehaviourPostfix(object __instance)
        {
            if (--modDepth != 0) return;
            double ms = (Stopwatch.GetTimestamp() - modStart) * TicksToMs;
            Account(ModOf(__instance.GetType().Assembly) + "/behaviours", ms);
        }

        static string Env(string k, string d) { var v = Environment.GetEnvironmentVariable(k); return string.IsNullOrEmpty(v) ? d : v; }

        public static void ProcessPrefix() { tickStart = Stopwatch.GetTimestamp(); armed = true; }
        public static void ProcessMainPostfix()
        {
            if (!armed) return;
            armed = false;
            int p = Phase;
            if (p < 1 || p > 4) return;
            double ms = (Stopwatch.GetTimestamp() - tickStart) * TicksToMs;
            PhaseTicks[p].Add(ms);
            int step = LadderStep;
            TickSeries.Add(new[] { Clock.Elapsed.TotalMilliseconds, ms, p == 4 && step > 0 ? 40 + step : p });
        }

        void OnRunGame()
        {
            startupMs = (DateTime.Now - proc.StartTime).TotalMilliseconds; startupClockMs = Clock.Elapsed.TotalMilliseconds;
            runPhases["RunGame"] = startupMs;
            result["label"] = label; result["variant"] = label; result["mode"] = mode; result["radius"] = radius;
            result["entity_count_requested"] = entityCount;
            result["startup_ms"] = startupMs;
            result["run_phases_ms"] = runPhases;
            result["seed"] = sapi.World.Seed;
            result["cpu"] = Environment.ProcessorCount;
            result["runtime"] = System.Runtime.InteropServices.RuntimeInformation.FrameworkDescription;
            result["gc_server"] = System.Runtime.GCSettings.IsServerGC;
            result["game_version"] = Vintagestory.API.Config.GameVersion.ShortGameVersion;

            // loaded mods + assembly -> mod map for attribution
            var builtin = new HashSet<string> { "game", "creative", "survival", "suhbench" };
            var mods = new List<Dictionary<string, object>>();
            foreach (var mod in sapi.ModLoader.Mods)
            {
                var info = mod.Info;
                mods.Add(new Dictionary<string, object>
                {
                    ["modid"] = info?.ModID, ["name"] = info?.Name, ["version"] = info?.Version, ["side"] = info?.Side.ToString(),
                    ["file"] = mod.FileName, ["builtin"] = builtin.Contains(info?.ModID ?? ""),
                    ["authors"] = info?.Authors?.ToArray(),
                });
                foreach (var sys in mod.Systems) { var a = sys.GetType().Assembly; if (!AsmToMod.ContainsKey(a)) AsmToMod[a] = info?.ModID == "suhbench" ? "suhbench" : builtin.Contains(info?.ModID ?? "") ? "game" : info?.ModID ?? "unknown"; }
            }
            result["mods"] = mods;
            result["mods_under_test"] = mods.Where(m => !(bool)m["builtin"]).Select(m => (string)m["modid"]).ToArray();
            if (ModTime.Count > 0) { try { PatchModBehaviours(); } catch (Exception e) { sapi.Logger.Warning("[SuhBench] behaviour patching failed: {0}", e.Message); } }
            sapi.Logger.Notification("[SuhBench] RunGame reached after {0:0} ms with {1} mods ({2} under test), starting worldgen phase", startupMs, mods.Count, ((string[])result["mods_under_test"]).Length);

            tickListenerId = sapi.Event.RegisterGameTickListener(OnTick, 250);
            if (Env("BENCH_WAIT_PLAYER", "0") == "1") { waitingForPlayer = true; waitDeadlineMs = Clock.Elapsed.TotalMilliseconds + 180000; sapi.Logger.Notification("[SuhBench] waiting for a player to join before starting"); return; }
            StartWorldgen();
        }

        bool waitingForPlayer; double waitDeadlineMs;
        void StartWorldgen()
        {
            result["players_online_at_start"] = sapi.World.AllOnlinePlayers.Length;
            result["player_names"] = sapi.World.AllOnlinePlayers.Select(pl => pl.PlayerName).ToArray();
            BeginPhase(1);

            var spawn = sapi.World.DefaultSpawnPosition;
            int cx = (int)spawn.X / 32, cz = (int)spawn.Z / 32;
            result["spawn_chunk"] = new[] { cx, cz };
            var cols = new List<int[]>();
            for (int dz = -radius; dz <= radius; dz++)
                for (int dx = -radius; dx <= radius; dx++)
                    cols.Add(new[] { cx + dx, cz + dz });
            cols.Sort((a, b) => (Math.Abs(a[0] - cx) + Math.Abs(a[1] - cz)).CompareTo(Math.Abs(b[0] - cx) + Math.Abs(b[1] - cz)));
            totalColumns = cols.Count;
            foreach (var c in cols)
            {
                sapi.WorldManager.LoadChunkColumnPriority(c[0], c[1], new ChunkLoadOptions
                {
                    KeepLoaded = true,
                    OnLoaded = () => System.Threading.Interlocked.Increment(ref loadedColumns)
                });
            }
            sapi.Logger.Notification("[SuhBench] requested {0} chunk columns (radius {1}) around chunk {2},{3}", totalColumns, radius, cx, cz);
        }

        void BeginPhase(int p)
        {
            PhaseTicks[p] = new List<double>();
            if (SysTime.ContainsKey(p)) SysTime[p] = new Dictionary<string, double[]>();
            if (ModTime.ContainsKey(p)) ModTime[p] = new Dictionary<string, double[]>();
            if (ListenerTypes.ContainsKey(p)) ListenerTypes[p] = new Dictionary<string, double[]>();
            Phase = p;
            phaseStartMs = Clock.Elapsed.TotalMilliseconds;
            phaseStartCpu = proc.TotalProcessorTime;
            phaseStartGcPause = GC.GetTotalPauseDuration().Ticks;
            for (int g = 0; g < 3; g++) phaseStartGc[g] = GC.CollectionCount(g);
        }

        Dictionary<string, object> EndPhase(string name, Dictionary<string, object> extra = null)
        {
            int p = Phase;
            Phase = 0;
            proc.Refresh();
            var ticks = PhaseTicks[p];
            var d = new Dictionary<string, object>
            {
                ["wall_ms"] = Clock.Elapsed.TotalMilliseconds - phaseStartMs,
                ["cpu_ms"] = (proc.TotalProcessorTime - phaseStartCpu).TotalMilliseconds,
                ["gc_pause_ms"] = (GC.GetTotalPauseDuration().Ticks - phaseStartGcPause) / 10000.0,
                ["gc_gen0"] = GC.CollectionCount(0) - phaseStartGc[0],
                ["gc_gen1"] = GC.CollectionCount(1) - phaseStartGc[1],
                ["gc_gen2"] = GC.CollectionCount(2) - phaseStartGc[2],
                ["tick_count"] = ticks.Count,
                ["tick_mean_ms"] = ticks.Count > 0 ? ticks.Average() : 0,
                ["tick_p50_ms"] = Pct(ticks, 0.50),
                ["tick_p95_ms"] = Pct(ticks, 0.95),
                ["tick_p99_ms"] = Pct(ticks, 0.99),
                ["tick_max_ms"] = ticks.Count > 0 ? ticks.Max() : 0,
                ["ticks"] = ticks.ToArray(),
                ["working_set_end_mb"] = proc.WorkingSet64 / 1048576.0,
                ["managed_heap_end_mb"] = GC.GetTotalMemory(false) / 1048576.0,
            };
            if (SysTime.TryGetValue(p, out var st)) d["systems_ms"] = st.OrderByDescending(kv => kv.Value[0]).ToDictionary(kv => kv.Key, kv => new { total_ms = kv.Value[0], calls = kv.Value[1], max_ms = kv.Value[2] });
            if (ListenerTypes.TryGetValue(p, out var lt)) d["listener_types_ms"] = lt.OrderByDescending(kv => kv.Value[0]).Take(25).ToDictionary(kv => kv.Key, kv => new { total_ms = kv.Value[0], calls = kv.Value[1], max_ms = kv.Value[2] });
            if (ModTime.TryGetValue(p, out var mt)) d["mods_ms"] = mt.OrderByDescending(kv => kv.Value[0]).ToDictionary(kv => kv.Key, kv => new { total_ms = kv.Value[0], calls = kv.Value[1], max_ms = kv.Value[2] });
            if (extra != null) foreach (var kv in extra) d[kv.Key] = kv.Value;
            if (name != null) result[name] = d;
            sapi.Logger.Notification("[SuhBench] phase {0} done: wall {1:0} ms, cpu {2:0} ms, ticks {3}, mean {4:0.00} ms, p99 {5:0.00} ms",
                name ?? "ladder", d["wall_ms"], d["cpu_ms"], ticks.Count, d["tick_mean_ms"], d["tick_p99_ms"]);
            return d;
        }

        static double Pct(List<double> v, double p)
        {
            if (v.Count == 0) return 0;
            var s = v.OrderBy(x => x).ToArray();
            double idx = p * (s.Length - 1); int lo = (int)Math.Floor(idx); int hi = Math.Min(lo + 1, s.Length - 1);
            return s[lo] + (s[hi] - s[lo]) * (idx - lo);
        }

        void OnTick(float dt)
        {
            double now = Clock.Elapsed.TotalMilliseconds;
            if (waitingForPlayer)
            {
                var pls = sapi.World.AllOnlinePlayers;
                if (pls.Length > 0 && pls.All(pl => pl.Entity != null))
                {
                    waitingForPlayer = false;
                    sapi.Logger.Notification("[SuhBench] player present: {0}; starting worldgen phase {1:0} ms after RunGame", string.Join(",", pls.Select(pl => pl.PlayerName)), now - startupClockMs);
                    StartWorldgen();
                }
                else if (now > waitDeadlineMs) { result["error"] = "no player joined within 180 s"; sapi.Logger.Error("[SuhBench] no player joined; aborting"); Finish(); }
                return;
            }
            proc.Refresh();
            samples.Add(new Dictionary<string, object>
            {
                ["t_ms"] = now, ["phase"] = Phase,
                ["loaded_columns"] = loadedColumns,
                ["working_set_mb"] = proc.WorkingSet64 / 1048576.0,
                ["managed_heap_mb"] = GC.GetTotalMemory(false) / 1048576.0,
                ["threads"] = proc.Threads.Count,
                ["entities"] = sapi.World.LoadedEntities.Count,
                ["cpu_ms"] = proc.TotalProcessorTime.TotalMilliseconds,
            });

            switch (Phase)
            {
                case 1:
                    if (loadedColumns >= totalColumns)
                    {
                        EndPhase("worldgen", new Dictionary<string, object> { ["columns"] = totalColumns, ["chunks"] = totalColumns * (sapi.WorldManager.MapSizeY / 32) });
                        BeginPhase(2);
                        phaseDeadlineMs = now + settleSec * 1000.0;
                    }
                    else if (now - phaseStartMs > 20 * 60 * 1000)
                    {
                        sapi.Logger.Error("[SuhBench] worldgen timed out with {0}/{1} columns", loadedColumns, totalColumns);
                        result["error"] = "worldgen timeout"; Finish();
                    }
                    break;
                case 2:
                    if (now >= phaseDeadlineMs)
                    {
                        EndPhase("settle", new Dictionary<string, object> { ["entities_present"] = sapi.World.LoadedEntities.Count });
                        PlaceBlocks();
                        BeginPhase(3);
                        phaseDeadlineMs = now + idleSec * 1000.0;
                    }
                    break;
                case 3:
                    if (now >= phaseDeadlineMs)
                    {
                        EndPhase("idle", new Dictionary<string, object> { ["entities_present"] = sapi.World.LoadedEntities.Count });
                        if (ladder.Length > 0) { result["ladder_targets"] = ladder; result["ladder_step_sec"] = stepSec; NextLadderStep(); }
                        else if (entityCount > 0) { SpawnEntities(entityCount); BeginPhase(4); phaseDeadlineMs = now + entitySec * 1000.0; }
                        else Finish();
                    }
                    break;
                case 0:
                    if (spawning)
                    {
                        int n = Math.Min(spawnPerTick, spawnQueue);
                        if (n > 0) { SpawnEntities(n); spawnQueue -= n; }
                        if (spawnQueue <= 0)
                        {
                            spawning = false;
                            sapi.Logger.Notification("[SuhBench] ladder step {0}: target {1}, loaded entities {2}", ladderIdx + 1, ladder[ladderIdx], sapi.World.LoadedEntities.Count);
                            LadderStep = ladderIdx + 1; BeginPhase(4); phaseDeadlineMs = now + stepSec * 1000.0;
                        }
                    }
                    break;
                case 4:
                    if (now >= phaseDeadlineMs && LadderStep > 0)
                    {
                        int activeL = sapi.World.LoadedEntities.Values.Count(e => e.State == EnumEntityState.Active);
                        var d = EndPhase(null, new Dictionary<string, object>
                        {
                            ["step"] = LadderStep, ["entities_target"] = ladder[ladderIdx], ["entities_spawned_total"] = spawnedEntities,
                            ["entities_end"] = sapi.World.LoadedEntities.Count, ["entities_active_end"] = activeL,
                        });
                        d.Remove("ticks");
                        ladderResults.Add(d); result["ladder"] = ladderResults;
                        LadderStep = 0;
                        double mean = (double)d["tick_mean_ms"];
                        if (ladderIdx + 1 >= ladder.Length || mean > ladderStopMs)
                        {
                            if (mean > ladderStopMs) sapi.Logger.Notification("[SuhBench] ladder stopped early: mean tick {0:0} ms exceeds {1:0} ms", mean, ladderStopMs);
                            Finish();
                        }
                        else NextLadderStep();
                    }
                    else if (now >= phaseDeadlineMs)
                    {
                        int active = sapi.World.LoadedEntities.Values.Count(e => e.State == EnumEntityState.Active);
                        EndPhase("entities", new Dictionary<string, object>
                        {
                            ["entities_spawned"] = spawnedEntities,
                            ["entities_end"] = sapi.World.LoadedEntities.Count,
                            ["entities_active_end"] = active,
                            ["codes"] = spawnedCodes.Distinct().ToArray(),
                        });
                        Finish();
                    }
                    break;
            }
        }

        void NextLadderStep()
        {
            ladderIdx++;
            spawnQueue = Math.Max(0, ladder[ladderIdx] - spawnedEntities);
            spawning = true; Phase = 0; LadderStep = 0;
            sapi.Logger.Notification("[SuhBench] ladder step {0}: spawning {1} more entities toward {2}", ladderIdx + 1, spawnQueue, ladder[ladderIdx]);
        }

        // BENCH_PLACE="primitivesurvival:fishbasket-north=40,game:firepit-lit=20": set that many of each block at random surface
        // positions around spawn before the idle phase, so mods whose cost lives in block entities have something to tick.
        // Unknown codes (the mod is not loaded in this variant) are skipped and reported, so the same setting fits every variant.
        void PlaceBlocks()
        {
            var spec = Env("BENCH_PLACE", "");
            if (spec.Length == 0) return;
            var rnd = new Random(4321); var spawn = sapi.World.DefaultSpawnPosition; int range = Math.Max(16, (radius - 2) * 32);
            var placed = new Dictionary<string, object>();
            foreach (var item in spec.Split(',', StringSplitOptions.RemoveEmptyEntries))
            {
                var parts = item.Split('='); string code = parts[0].Trim(); int count = parts.Length > 1 ? int.Parse(parts[1]) : 10;
                var block = sapi.World.GetBlock(new AssetLocation(code));
                if (block == null) block = sapi.World.Blocks.FirstOrDefault(b => b?.Code != null && b.Code.ToString().StartsWith(code));
                if (block == null) { placed[code] = "not available"; sapi.Logger.Notification("[SuhBench] place: block {0} not available in this variant, skipped", code); continue; }
                int ok = 0, be = 0;
                for (int i = 0; i < count; i++)
                {
                    int x = (int)spawn.X + rnd.Next(-range, range + 1), z = (int)spawn.Z + rnd.Next(-range, range + 1);
                    int y = sapi.World.BlockAccessor.GetRainMapHeightAt(x, z);
                    if (y <= 0) continue;
                    var pos = new BlockPos(x, y + 1, z);
                    if (sapi.World.BlockAccessor.GetBlock(pos).Id != 0) continue;
                    try { sapi.World.BlockAccessor.SetBlock(block.BlockId, pos); ok++; if (sapi.World.BlockAccessor.GetBlockEntity(pos) != null) be++; } catch (Exception e) { sapi.Logger.Warning("[SuhBench] place {0} failed: {1}", code, e.Message); break; }
                }
                placed[block.Code.ToString()] = ok;
                sapi.Logger.Notification("[SuhBench] placed {0} x {1} (entity class {2}, {3} block entities present)", ok, block.Code, block.EntityClass ?? "none", be);
            }
            result["placed_blocks"] = placed;
        }

        Random spawnRnd = new Random(1234);
        int spawnSerial;
        void SpawnEntities(int count)
        {
            string[] codes = Env("BENCH_CREATURES", "wolf-eurasian-adult-male,drifter-normal,deer-whitetail-adult-female,fox-red-adult-male,hare-european-adult-female,drifter-deep").Split(',');
            var rnd = spawnRnd;
            var spawn = sapi.World.DefaultSpawnPosition;
            // BENCH_SPAWN_RANGE: half-width in blocks of the square creatures are spawned in (default: the loaded area);
            // BENCH_ALWAYS_ACTIVE=0 leaves creatures to the game's own (and the mods') distance-based activation, which only
            // makes sense with a player online. Default 1: every creature ticks regardless of distance, as in the Stratum test.
            int range = int.Parse(Env("BENCH_SPAWN_RANGE", Math.Max(32, (radius - 2) * 32).ToString()));
            bool alwaysActive = Env("BENCH_ALWAYS_ACTIVE", "1") == "1";
            result["spawn_range"] = range; result["creatures_always_active"] = alwaysActive;
            int ok = 0, fail = 0;
            for (int i = 0; i < count; i++)
            {
                string code = codes[spawnSerial++ % codes.Length].Trim();
                var type = sapi.World.GetEntityType(new AssetLocation(code.Contains(':') ? code : "game:" + code));
                if (type == null) { fail++; if (fail < 5) sapi.Logger.Warning("[SuhBench] unknown entity {0}", code); continue; }
                double x = spawn.X + rnd.Next(-range, range + 1) + 0.5;
                double z = spawn.Z + rnd.Next(-range, range + 1) + 0.5;
                int y = sapi.World.BlockAccessor.GetRainMapHeightAt((int)x, (int)z);
                if (y <= 0) { fail++; continue; }
                var entity = sapi.ClassRegistry.CreateEntity(type);
                entity.ServerPos.SetPos(x, y + 1.5, z);
                entity.ServerPos.Yaw = (float)(rnd.NextDouble() * Math.PI * 2);
                entity.Pos.SetFrom(entity.ServerPos);
                entity.AlwaysActive = alwaysActive;
                sapi.World.SpawnEntity(entity);
                if (alwaysActive) entity.State = EnumEntityState.Active;
                entity.SidedProperties?.Behaviors?.RemoveAll(b => b.PropertyName() == "timeddespawn");
                ok++; spawnedCodes.Add(code);
            }
            spawnedEntities += ok;
            if (ladder.Length == 0 || fail > 0) sapi.Logger.Notification("[SuhBench] spawned {0} entities ({1} failed), loaded entities now {2}", ok, fail, sapi.World.LoadedEntities.Count);
        }

        void Finish()
        {
            Phase = 5;
            sapi.Event.UnregisterGameTickListener(tickListenerId);
            proc.Refresh();
            result["total_cpu_ms"] = proc.TotalProcessorTime.TotalMilliseconds;
            result["peak_working_set_mb"] = proc.PeakWorkingSet64 / 1048576.0;
            result["samples"] = samples;
            result["tick_series"] = TickSeries;
            result["finished_utc"] = DateTime.UtcNow.ToString("o");
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(outPath));
                File.WriteAllText(outPath, JsonSerializer.Serialize(result));
                sapi.Logger.Notification("[SuhBench] wrote {0}", outPath);
            }
            catch (Exception e) { sapi.Logger.Error("[SuhBench] failed to write result: {0}", e); }
            sapi.Logger.Notification("[SuhBench] shutting down");
            sapi.Server.ShutDown();
        }

        public override void Dispose() { harmony?.UnpatchAll("suh.bench"); }
    }
}
