# Warcraft III FPS-unlock patch set

These are patched copies of the 11 `game.dll` files in `War3Launcher/versions`. The original version files were not changed. SHA-256 values below identify the copied DLLs; the four early `war3.exe` companions are also patched because those versions keep the software 64 FPS cap in the EXE, not in `game.dll`.

## What is patched

| Version family | Changes |
| --- | --- |
| 1.0.17.5988–1.21.0.6263 | D3D8 exclusive-fullscreen presentation interval, OpenGL swap interval. Also includes the necessary `war3.exe` software-cap patch. |
| 1.22.0.6328–1.26.0.6401 | Software 64 FPS flag, D3D8 exclusive-fullscreen presentation interval, default `maxfps` 200 → 10000, OpenGL swap interval. |
| 1.27.0.52240 | Software 64 FPS flag, D3D9 exclusive-fullscreen and windowed presentation interval, clear `LOCKABLE_BACKBUFFER`, default `maxfps` 200 → 10000, OpenGL swap interval. |

The D3D8 windowed path is deliberately not forced to `IMMEDIATE`: some D3D8 devices reject that interval or require the lockable-backbuffer flag. Consequently, windowed D3D8 may still be synchronized to the display. Existing `Video\maxfps` registry values take precedence over the patched default; `0` is not an unlimited value.

The OpenGL patch uses position-independent code and does not rely on a fixed image base. It applies `wglSwapIntervalEXT(0)` after the original context setup call.

## Patched DLL inventory

| Version | Output folder | Patched `game.dll` SHA-256 |
| --- | --- | --- |
| 1.0.17.5988 | `1.0.17.5988-fps-unlock-dx-ogl` | `ee5e1d9144af32dc3543834aaf1c54a90e68ff3ec62ed757d086bddab64bea10` |
| 1.0.20.6048 | `1.0.20.6048-fps-unlock-dx-ogl` | `1ccfe61c089d58dce5b2c505953d285c569d49d0357ac4c1ce358692e43c9378` |
| 1.20.4.6074 | `1.20.4.6074-fps-unlock-dx-ogl` | `a1dc3e75476862510c42da38668d4eab7100a3a584e6f9a2729ba85b55307a94` |
| 1.21.0.6263 | `1.21.0.6263-fps-unlock-dx-ogl` | `08f7cf777f22a721c08aa64ee5c7b9aad41ade0b8ae3a546c81b99ef4d73633c` |
| 1.22.0.6328 | `1.22.0.6328-fps-unlock-dx-ogl` | `42b61b2301227df5a84e67d84fae6b5f7d5b89fc5f01fd36ba8d1dd000a1be56` |
| 1.23.0.6352 | `1.23.0.6352-fps-unlock-dx-ogl` | `a5601f9cb52bbe0d23a8de1086605e002c7db164745ba26d97ae1ddd0b0e8874` |
| 1.24.1.6374 | `1.24.1.6374-fps-unlock-dx-ogl` | `2ca0e1d5e17542cebb6566fbd510c663501e6925efb3105af4f599c760c096e2` |
| 1.24.4.6387 | `1.24.4.6387-fps-unlock-dx-ogl` | `802feb939f82de838f77fd9a5bc936f15fe798ee647849b1775d9a08b55fcb45` |
| 1.25.1.6397 | `1.25.1.6397-fps-unlock-dx-ogl` | `717279b5268515f95dfb1fd9f2463d8f8f26442c40c1ca119499c619e1396455` |
| 1.26.0.6401 | `1.26.0.6401-fps-unlock-dx-ogl` | `d4787840e4f3f1b14c2a8047b4c51fa964e730de0b499f10f2a8e3485586c5ec` |
| 1.27.0.52240 | `1.27.0.52240-fps-unlock-dx-ogl` | `4c03df5a82efab9c7011b8f283ee427b8e2b78e96916992bfa39886dcc21d17c` |

For compatibility with the earlier directory name, `1.27.0.52240-fps-unlock-d3d9-ogl/game.dll` is an identical copy of the 1.27 DLL above.

## Required early-version EXE companions

Replace the matching `war3.exe` as well as `game.dll` for these versions. Without the EXE, the software 64 FPS cap remains.

| Version | Patched `war3.exe` SHA-256 |
| --- | --- |
| 1.0.17.5988 | `b2525fc0e58d87ee7fc0c5d860ae6ee1b52ee45899c5d00f2f3f022fd0b420bd` |
| 1.0.20.6048 | `c39705648d5cad43594b70ed526cfb62b37d4f1b6db516afecb31cb9b84f2bfe` |
| 1.20.4.6074 | `57a3852d9ccf173f010a8e1bb80f80b1d2a8cc56c219cf6dccf2e207b47b24ee` |
| 1.21.0.6263 | `663d742504d5548892a1f4ffb542d9ca0d5ec460cd2fac0b2a91d45cd0521172` |

## Verification and use

- Each patched DLL was reconstructed in memory from its corresponding original with the existing byte-checked patcher, then compared byte-for-byte with this output. The four EXE companions were checked the same way.
- All copied output DLLs and EXEs were also compared by SHA-256 against the existing generated patch set.
- These checks establish static byte identity only. The patched builds have not been run through all game versions or render paths; test them in a separate game copy and retain backups.
- Start with exclusive-fullscreen Direct3D for D3D8 versions; test `-opengl` separately. For 1.27, test both fullscreen and windowed paths.
- Do not select another launcher version during testing if it restores files from `War3Launcher/versions`.
- This set does not change `War3Launcher/hooker/war3hook.cpp`. Its resolution-change crash/hang is a separate runtime-hook issue; see `War3Analysis/analyses/warcraft-iii-fps-runtime-hooks.md`.
