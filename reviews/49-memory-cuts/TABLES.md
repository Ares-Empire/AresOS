All memory in MiB; paired savings are baseline minus factor, positive means less memory. Ranges are observed, not confidence intervals.

Isolated factors and covered experiments use the original common mod tree. Combined validation uses fresh controls from the merged tree; see [source-refresh.json](source-refresh.json) and the provenance audit.

Retained candidate: [compact headers + native interval + arena cap](candidates/compact-headers-native/candidate.json) — not qualified: first-creation standing/flight frames worse than paired current v1. Its control/trial are excluded from the final candidate's means.

Retained candidate: [native trim every60s + arena cap2](candidates/native-interval-arena/candidate.json) — not qualified: second flat flight had34.916ms frame versus paired current control11.565ms, with one extra >33ms frame. Its control/trial are excluded from the final candidate's means.

| Factor | Research estimate | Settled RSS saving, mean (range) | Post-flight RSS saving | Covered 5-min RSS saving | Standing post-G1 heap minimum saving |
|---|---|---:|---:|---:|---:|
| compact headers | 30–60 | 28.0 (-33–89; n=2) | 50.0 (15–85; n=2) | 50.5 (16–85; n=2) | 20.0 (17–23; n=2) |
| compact headers + string dedup | 0–20 extra over headers | 5.0 (-62–72; n=2) | -42.0 (-177–93; n=2) | -25.0 (-151–101; n=2) | 25.5 (22–29; n=2) |
| native trim every 60 s | 50–200 native total | 188.0 (170–206; n=2) | 233.5 (184–283; n=2) | 260.0 (220–300; n=2) | 0.5 (-2–3; n=2) |
| 60 s trim + LWJGL system allocator | 50–200 native total; not additive | 186.5 (142–231; n=2) | 187.0 (141–233; n=2) | 200.5 (153–248; n=2) | 2.0 (0–4; n=2) |
| MALLOC_ARENA_MAX=2 | 50–200 native total; not additive | 183.5 (182–185; n=2) | 271.5 (248–295; n=2) | 273.5 (244–303; n=2) | -0.5 (-1–0; n=2) |
| GC/background thread limits | 10–40 | -8.5 (-57–40; n=2) | 65.5 (47–84; n=2) | 35.5 (32–39; n=2) | 2.5 (-1–6; n=2) |
| FerriteCore 9.0.0 | 15–45 | -17.0 (-56–22; n=2) | -53.5 (-95–-12; n=2) | -62.5 (-106–-19; n=2) | 10.5 (9–12; n=2) |

Accounting residual: RssAnon − (NMT total committed − shared class space). Committed bytes are not resident bytes: this is a rough residual, not a measured allocator heap. Positive paired savings mean a smaller residual.

| Factor | Settled residual saving | Post-flight residual saving | Covered residual saving | Post-flight committed Java heap saving |
|---|---:|---:|---:|---:|
| compact headers | 15.0 (5–25; n=2) | 21.5 (11–32; n=2) | 24.0 (19–29; n=2) | 29.5 (6–53; n=2) |
| compact headers + string dedup | -45.0 (-116–26; n=2) | -25.5 (-99–48; n=2) | -29.0 (-109–51; n=2) | -9.0 (-72–54; n=2) |
| native trim every 60 s | 197.0 (159–235; n=2) | 183.5 (169–198; n=2) | 223.5 (205–242; n=2) | 51.5 (17–86; n=2) |
| 60 s trim + LWJGL system allocator | 160.5 (107–214; n=2) | 187.0 (142–232; n=2) | 191.0 (140–242; n=2) | 10.5 (7–14; n=2) |
| MALLOC_ARENA_MAX=2 | 192.0 (169–215; n=2) | 287.0 (251–323; n=2) | 292.0 (250–334; n=2) | -15.0 (-22–-8; n=2) |
| GC/background thread limits | -28.5 (-35–-22; n=2) | -23.5 (-43–-4; n=2) | -29.5 (-43–-16; n=2) | 65.5 (24–107; n=2) |
| FerriteCore 9.0.0 | -63.0 (-94–-32; n=2) | -77.0 (-115–-39; n=2) | -92.0 (-134–-50; n=2) | 25.5 (22–29; n=2) |

Current-source final candidate ([settings](winners.json)); fresh v1 controls and candidate runs, planned n=3 each; cells show the recorded n. These absolute ranges and paired differences are measured directly, not summed from isolated factors.

| Current-source group | Settled RSS | Post-flight RSS | Covered 5-min RSS |
|---|---:|---:|---:|
| fresh v1 | 1184.3 (1165–1210; n=3) | 1359.3 (1263–1457; n=3) | 1318.3 (1235–1404; n=3) |
| final candidate | 1017.0 (1011–1024; n=3) | 1064.3 (1050–1078; n=3) | 1037.3 (1024–1051; n=3) |
| paired RSS saving | 167.3 (154–194; n=3) | 295.0 (198–379; n=3) | 281.0 (198–353; n=3) |

Covered actions use v1 settings. Each saving below compares with the untreated run in the same round; these are independent JVMs, so inspect the pre-action RSS too. zram is device-wide and includes other builders. Its physical-memory change is not an attributed game cost.

| Covered run / status | RSS before / 5 min / wake | Saving vs untreated 5 min | Scope swap 5 min / wake | Global zram original / compressed / physical at 5 min (physical change) | Majflt covered / wake | Return to first frame ms | Wake worst; >17 / >33 ms | GC max after join ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| cover-freeze-1 (FAILED; wake incomplete) | 1287 / 510 / — | 714 | 598 / — | 5953.9 / 2027.7 / 2059.6 (+115.8) | 481 / — | — | —; — / — | 67.13 |
| cover-freeze-2 (FAILED; wake incomplete) | 1308 / 494 / — | 800 | 599 / — | 5953.6 / 2029.6 / 2061.3 (+117.7) | 153 / — | — | —; — / — | 69.65 |
| cover-gc-1 (complete) | 1256 / 1088 / 1089 | 136 | 0 / 0 | 5397.7 / 1883.5 / 1944.7 (-0.0) | 0 / 0 | 68.07 | 33.7; 13 / 12 | 73.28 |
| cover-gc-2 (complete) | 1247 / 1091 / 1091 | 203 | 0 / 0 | 5367.3 / 1875.0 / 1906.6 (+0.0) | 0 / 0 | 72.27 | 33.5; 12 / 11 | 74.66 |
| cover-none-1 (complete) | 1248 / 1224 / 1224 | 0 | 0 / 0 | 5398.3 / 1883.6 / 1944.7 (+0.0) | 0 / 0 | 56.51 | 33.5; 12 / 12 | 11.69 |
| cover-none-2 (complete) | 1320 / 1294 / 1294 | 0 | 0 / 0 | 5367.2 / 1875.0 / 1906.6 (+0.0) | 0 / 0 | 72.32 | 33.8; 13 / 12 | 11.54 |
| cover-r300-1 (complete) | 1261 / 991 / 995 | 233 | 98 / 96 | 5479.0 / 1905.9 / 1972.0 (+27.3) | 52800 / 497 | 80.57 | 41.8; 12 / 12 | 69.84 |
| cover-r300-2 (complete) | 1251 / 992 / 996 | 302 | 99 / 96 | 5476.4 / 1905.8 / 1973.2 (+29.6) | 52478 / 623 | 74.15 | 33.5; 12 / 12 | 72.83 |
| cover-r600-1 (complete) | 1244 / 804 / 810 | 420 | 251 / 247 | 5618.1 / 1941.6 / 2031.5 (+86.9) | 84289 / 1258 | 95.03 | 53.1; 12 / 11 | 80.08 |
| cover-r600-2 (complete) | 1319 / 772 / 778 | 522 | 341 / 334 | 5694.8 / 1956.5 / 2014.7 (+71.0) | 59757 / 1794 | 110.7 | 62.9; 12 / 12 | 71.05 |

| Run | Start to join s | Settled RSS / PSS | Post-flight RSS | Covered 5-min RSS / scope swap | Flight p99 / worst ms | Wake worst; >17 / >33 ms | Wake first frame ms | Majflt cover+wake | GC max after join ms | OOM / high / lost frames |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| arenas-1 | 9.59 | 1100 / 994 | 1116 | 1088 / 0 | 8.52 / 12.8 | 33.9; 13 / 11 | 26.35 | 0 | 15.48 | False / 0 / 0 |
| arenas-2 | 9.58 | 1071 / 964 | 1081 | 1057 / 0 | 8.51 / 11.6 | 33.6; 13 / 12 | 17.18 | 0 | 15.57 | False / 0 / 0 |
| coh-1 | 9.59 | 1270 / 1165 | 1354 | 1329 / 0 | 8.49 / 11.7 | 33.7; 12 / 11 | 26.99 | 0 | 11.96 | False / 0 / 0 |
| coh-2 | 10.09 | 1317 / 1212 | 1379 | 1354 / 0 | 8.51 / 12.1 | 36.4; 12 / 12 | 36.37 | 0 | 18.99 | False / 0 / 0 |
| cover-gc-1 | 9.59 | 1183 / 1075 | 1256 | 1088 / 0 | 8.52 / 16.7 | 33.7; 13 / 12 | 19.61 | 0 | 73.28 | False / 0 / 0 |
| cover-gc-2 | 9.58 | 1182 / 1076 | 1247 | 1091 / 0 | 8.52 / 27.0 | 33.5; 12 / 11 | 28.04 | 0 | 74.66 | False / 0 / 0 |
| cover-none-1 | 9.58 | 1208 / 1103 | 1243 | 1224 / 0 | 8.51 / 16.8 | 33.5; 12 / 12 | 8.57 | 0 | 11.69 | False / 0 / 0 |
| cover-none-2 | 10.09 | 1217 / 1112 | 1316 | 1294 / 0 | 8.53 / 17.2 | 33.8; 13 / 12 | 30.35 | 0 | 11.54 | False / 0 / 0 |
| cover-r300-1 | 9.08 | 1165 / 1057 | 1261 | 991 / 98 | 8.53 / 14.7 | 41.8; 12 / 12 | 41.84 | 53297 | 69.84 | False / 0 / 0 |
| cover-r300-2 | 9.58 | 1156 / 1051 | 1247 | 992 / 99 | 8.52 / 12.1 | 33.5; 12 / 12 | 33.24 | 53101 | 72.83 | False / 0 / 0 |
| cover-r600-1 | 9.08 | 1149 / 1045 | 1241 | 804 / 251 | 8.52 / 11.4 | 53.1; 12 / 11 | 53.14 | 85547 | 80.08 | False / 0 / 0 |
| cover-r600-2 | 9.08 | 1138 / 1033 | 1319 | 772 / 341 | 8.48 / 11.1 | 62.9; 12 / 12 | 62.91 | 61551 | 71.05 | False / 0 / 0 |
| dedup-1 | 10.09 | 1249 / 1147 | 1318 | 1288 / 3 | 8.56 / 23.3 | 60.3; 12 / 12 | 60.26 | 88 | 15.29 | False / 0 / 0 |
| dedup-2 | 9.59 | 1277 / 1173 | 1447 | 1399 / 0 | 8.54 / 14.2 | 33.6; 12 / 11 | 20.27 | 0 | 15.17 | False / 0 / 0 |
| ferrite-1 | 9.59 | 1280 / 1173 | 1374 | 1362 / 0 | 8.52 / 12.4 | 33.5; 12 / 11 | 30.0 | 0 | 14.23 | False / 0 / 0 |
| ferrite-2 | 9.08 | 1211 / 1106 | 1293 | 1275 / 0 | 8.53 / 19.9 | 33.4; 12 / 11 | 28.72 | 0 | 14.58 | False / 0 / 0 |
| s0-long | 9.59 | 1245 / 1136 | — | — / — | — / — | —; — / — | — | — | 12.84 | False / 0 / 0 |
| s0-probe | 9.59 | 1266 / 1160 | 1270 | 1132 / 0 | 8.53 / 14.4 | 66.4; 299 / 298 | 66.39 | 0 | 77.34 | False / 0 / 0 |
| setup-flat | 31.36 | 1145 / 1029 | — | — / — | — / — | —; — / — | — | — | 10.35 | False / 0 / 0 |
| setup-nether | 21.38 | 1139 / 1026 | — | 1099 / 0 | — / — | 33.5; 13 / 12 | 12.9 | 0 | 7.42 | False / 0 / 0 |
| system-1 | 9.58 | 1106 / 1001 | 1179 | 1143 / 0 | 8.51 / 18.0 | 56.6; 12 / 12 | 56.64 | 0 | 12.79 | False / 0 / 0 |
| system-2 | 9.58 | 1084 / 979 | 1136 | 1101 / 0 | 8.51 / 14.0 | 46.1; 12 / 12 | 46.08 | 0 | 13.09 | False / 0 / 0 |
| threads-1 | 10.08 | 1221 / 1115 | 1283 | 1268 / 0 | 8.51 / 15.2 | 73.3; 11 / 10 | 73.33 | 0 | 16.13 | False / 0 / 0 |
| threads-2 | 10.09 | 1218 / 1111 | 1290 | 1278 / 0 | 8.53 / 18.4 | 70.1; 11 / 11 | 70.12 | 0 | 14.97 | False / 0 / 0 |
| trim-1 | 9.59 | 1109 / 1005 | 1177 | 1114 / 0 | 8.53 / 18.5 | 73.3; 11 / 11 | 73.3 | 0 | 11.14 | False / 0 / 0 |
| trim-2 | 9.59 | 1016 / 910 | 1091 | 1028 / 0 | 8.54 / 15.6 | 33.8; 13 / 13 | 9.5 | 0 | 13.39 | False / 0 / 0 |
| v1-arenas-1 | 9.08 | 1282 / 1176 | 1411 | 1391 / 0 | 8.53 / 12.8 | 33.6; 12 / 11 | 30.51 | 0 | 11.48 | False / 0 / 0 |
| v1-arenas-2 | 12.1 | 1256 / 1149 | 1329 | 1301 / 0 | 8.52 / 11.8 | 57.1; 12 / 12 | 57.07 | 0 | 13.48 | False / 0 / 0 |
| v1-coh-1 | 9.08 | 1359 / 1252 | 1439 | 1414 / 0 | 8.47 / 11.6 | 33.4; 12 / 11 | 27.91 | 0 | 12.23 | False / 0 / 0 |
| v1-coh-2 | 9.59 | 1284 / 1177 | 1394 | 1370 / 0 | 8.54 / 12.6 | 33.5; 12 / 12 | 10.19 | 0 | 11.64 | False / 0 / 0 |
| v1-create | 9.69 | 1270 / 1155 | 1401 | 1383 / 0 | 8.58 / 13.9 | 36.9; 12 / 12 | 36.88 | 0 | 11.72 | False / 0 / 0 |
| v1-dedup-1 | 10.09 | 1321 / 1216 | 1411 | 1389 / 0 | 8.48 / 15.4 | 33.7; 12 / 10 | 13.86 | 0 | 12.64 | False / 0 / 0 |
| v1-dedup-2 | 9.59 | 1215 / 1109 | 1270 | 1248 / 0 | 8.51 / 11.3 | 51.5; 12 / 12 | 51.5 | 0 | 14.57 | False / 0 / 0 |
| v1-ferrite-1 | 9.08 | 1224 / 1117 | 1279 | 1256 / 0 | 8.51 / 12.1 | 50.9; 12 / 12 | 50.89 | 0 | 11.78 | False / 0 / 0 |
| v1-ferrite-2 | 9.59 | 1233 / 1128 | 1281 | 1256 / 0 | 8.56 / 17.7 | 77.1; 11 / 11 | 77.08 | 0 | 12.35 | False / 0 / 0 |
| v1-flat-1 | 9.58 | 1178 / 1071 | 1263 | 1235 / 0 | 8.55 / 15.1 | 75.1; 11 / 11 | 75.07 | 0 | 14.11 | False / 0 / 0 |
| v1-flat-2 | 9.08 | 1165 / 1060 | 1358 | 1316 / 0 | 8.6 / 14.3 | 33.8; 12 / 11 | 11.95 | 0 | 12.14 | False / 0 / 0 |
| v1-flat-3 | 9.59 | 1210 / 1103 | 1457 | 1404 / 0 | 8.49 / 11.4 | 33.6; 12 / 11 | 26.97 | 0 | 11.1 | False / 0 / 0 |
| v1-nether | 9.58 | 1185 / 1081 | 1482 | 1446 / 0 | 10.15 / 29.1 | 33.7; 14 / 12 | 22.76 | 0 | 13.63 | False / 0 / 0 |
| v1-system-1 | 9.59 | 1337 / 1232 | 1412 | 1391 / 0 | 8.52 / 13.2 | 33.6; 12 / 11 | 21.69 | 0 | 13.29 | False / 0 / 0 |
| v1-system-2 | 9.58 | 1226 / 1119 | 1277 | 1254 / 0 | 8.5 / 11.4 | 61.3; 11 / 11 | 61.34 | 0 | 12.53 | False / 0 / 0 |
| v1-threads-1 | 8.58 | 1164 / 1056 | 1367 | 1307 / 0 | 8.5 / 13.6 | 33.5; 12 / 12 | 0.43 | 0 | 11.67 | False / 0 / 0 |
| v1-threads-2 | 9.59 | 1258 / 1151 | 1337 | 1310 / 0 | 8.51 / 18.1 | 52.5; 12 / 12 | 52.52 | 0 | 15.58 | False / 0 / 0 |
| v1-trim-1 | 10.1 | 1279 / 1175 | 1460 | 1414 / 0 | 8.51 / 11.6 | 33.6; 12 / 12 | 7.84 | 0 | 11.43 | False / 0 / 0 |
| v1-trim-2 | 9.59 | 1222 / 1117 | 1275 | 1248 / 0 | 8.52 / 13.6 | 33.9; 12 / 12 | 33.93 | 0 | 13.49 | False / 0 / 0 |
| winner-create | 9.57 | 1100 / 984 | 1133 | 1109 / 0 | 8.52 / 14.1 | 33.6; 12 / 12 | 15.41 | 0 | 22.53 | False / 0 / 0 |
| winner-flat-1 | 9.59 | 1024 / 918 | 1065 | 1037 / 0 | 8.54 / 19.9 | 33.4; 12 / 11 | 29.6 | 0 | 11.55 | False / 0 / 0 |
| winner-flat-2 | 9.58 | 1011 / 907 | 1050 | 1024 / 0 | 8.54 / 13.8 | 40.8; 12 / 11 | 40.78 | 0 | 12.2 | False / 0 / 0 |
| winner-flat-3 | 9.58 | 1016 / 911 | 1078 | 1051 / 0 | 8.52 / 11.6 | 51.4; 12 / 12 | 51.38 | 0 | 10.94 | False / 0 / 0 |
| winner-long | 9.59 | 1022 / 918 | — | — / — | — / — | —; — / — | — | — | 13.59 | False / 0 / 0 |
| winner-nether | 9.58 | 1103 / 997 | 1295 | 1228 / 0 | 9.76 / 21.8 | 48.2; 13 / 12 | 48.16 | 0 | 20.01 | False / 0 / 0 |
| winner-nmt0 | 9.08 | 1056 / 949 | 1063 | 1038 / 0 | 8.49 / 22.3 | 51.1; 12 / 12 | 51.08 | 0 | 13.15 | False / 0 / 0 |
