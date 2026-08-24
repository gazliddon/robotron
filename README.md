# Robotron: 2084 (Gazm Toolchain)

This repository contains the complete assembly source code for Williams' classic arcade game **Robotron: 2084** (Solid Blue / Revision 6) including the **Main 6809 Board** and the **Sound 6800/6802/6808 Board**, structured and buildable using the **Gazm** toolchain.

## Building

To assemble the complete set of 12 Main Game ROM binaries and the Sound Board ROM binary:

```bash
gazm build
```

The resulting binaries are written to `roms/01` through `roms/12` and `roms/robotron.snd`.

## Verification & ROM Checksums

All 13 ROM images match the MAME Solid Blue (Revision 6) arcade release byte-for-byte:

### Main Board (Motorola 6809)

| ROM File | CPU Address | SHA-1 Checksum | Status |
| :--- | :--- | :--- | :--- |
| `roms/01` | `$0000` | `f6d60e26c209c1df2cc01ac07ad5559daa1b7118` | ✅ 100% Match |
| `roms/02` | `$1000` | `4d6e82bc29f49100f7751ccfc6a9ff35695b84b3` | ✅ 100% Match |
| `roms/03` | `$2000` | `06a8c8dd0b4726eb7f0bb0e89c8533931d75fc1c` | ✅ 100% Match |
| `roms/04` | `$3000` | `aaf89c19fd8f4e8750717169eb1af476aef38a5e` | ✅ 100% Match |
| `roms/05` | `$4000` | `79b4680ce19bd28882ae823f0e7b293af17cbb91` | ✅ 100% Match |
| `roms/06` | `$5000` | `f76ec5432a7939b33a27be1c6855e2dbe6d9fdc8` | ✅ 100% Match |
| `roms/07` | `$6000` | `06eae5138254723819a5e93cfd9e9f3285fcddf5` | ✅ 100% Match |
| `roms/08` | `$7000` | `7ae38a609ed9a6f62ca003cab719740ed7651b7c` | ✅ 100% Match |
| `roms/09` | `$8000` | `fd9d75b866f0ebbb723f84889337e6814496a103` | ✅ 100% Match |
| `roms/10` | `$D000` | `d426a50e75dabe936de643c83a548da5e399331c` | ✅ 100% Match |
| `roms/11` | `$E000` | `f8c6cbe3688f256f41a121255fc08f575f6a4b4f` | ✅ 100% Match |
| `roms/12` | `$F000` | `fad7cea868ebf17347c4bc5193d647bbd8f9517b` | ✅ 100% Match |

### Sound Board (Motorola 6800 / 6802 / 6808)

| ROM File | CPU Address | SHA-1 Checksum | Status |
| :--- | :--- | :--- | :--- |
| `roms/robotron.snd` | `$F000` | `15afefef11bfc3ab78f61ab046701db78d160ec3` | ✅ 100% Match |

To verify all checksums directly:
```bash
./checksumroms \
  f6d60e26c209c1df2cc01ac07ad5559daa1b7118 roms/01 \
  4d6e82bc29f49100f7751ccfc6a9ff35695b84b3 roms/02 \
  06a8c8dd0b4726eb7f0bb0e89c8533931d75fc1c roms/03 \
  aaf89c19fd8f4e8750717169eb1af476aef38a5e roms/04 \
  79b4680ce19bd28882ae823f0e7b293af17cbb91 roms/05 \
  f76ec5432a7939b33a27be1c6855e2dbe6d9fdc8 roms/06 \
  06eae5138254723819a5e93cfd9e9f3285fcddf5 roms/07 \
  7ae38a609ed9a6f62ca003cab719740ed7651b7c roms/08 \
  fd9d75b866f0ebbb723f84889337e6814496a103 roms/09 \
  d426a50e75dabe936de643c83a548da5e399331c roms/10 \
  f8c6cbe3688f256f41a121255fc08f575f6a4b4f roms/11 \
  fad7cea868ebf17347c4bc5193d647bbd8f9517b roms/12 \
  15afefef11bfc3ab78f61ab046701db78d160ec3 roms/robotron.snd
```

## Structure

- `src/robotron.gazm`: Master assembly file configuring module scopes, memory layouts, and ROM outputs for 6809 main board.
- `src/macros.gazm`: Williams assembly idiom macros (`makp`, `nap`, `sleep`, `mkprob`, `clc`, `sec`, etc.).
- `src/RRF.gazm`: Hardware equates, vector jump addresses, and Direct Page RAM layouts.
- `src/RRELESE6.gazm`: Release 6 ROM patches, unallocated EPROM padding (`$FF`), and vector checksum table.
- `src/*.gazm`: Converted 6809 assembly modules for each game subsystem.
- `snd_src/main.src`: Master assembly file for 6800 soundboard.
- `snd_src/vsndrm3.src`: Converted 6800 soundboard code (`VSNDRM3.SRC`).
- `gazm.toml`: Multi-target build configuration for both `robotron` (6809) and `sound` (6800).
