# 🚪 Blaze & Blade - Door Analysis System

Comprehensive door, key, and trigger analysis system for Blaze & Blade - Eternal Quest.

## 📁 Structure

```
Data/doors/
├── 📂 docs/                          Documentation
│   ├── README_START_HERE.txt         ← Start here!
│   ├── ANALYSE_COMPLETE.md           Full analysis report
│   ├── TRIGGER_TEST_GUIDE.md         Trigger testing methodology
│   ├── EXPLORATION_GUIDE.md          In-game cataloging guide
│   ├── SUMMARY.md                    Visual summary
│   ├── LISTE_PORTES_PAR_ZONE.txt     Complete list (French)
│   ├── README_TRIGGER_TESTING.txt    Quick trigger reference
│   └── STRUCTURE.txt                 Directory structure
│
├── 📂 scripts/                       Python tools
│   ├── test_triggers_system.py       Main trigger testing tool
│   └── analyze_trigger_format.py     Trigger format analyzer
│
├── 📂 trigger_tests/                 Test patches (225 MB)
│   ├── triggers_database.json        500 triggers extracted
│   ├── LEVELS_TEST_GROUP1.DAT        Test group 1 (triggers 1-20)
│   ├── LEVELS_TEST_GROUP2.DAT        Test group 2 (triggers 21-40)
│   ├── LEVELS_TEST_GROUP3.DAT        Test group 3 (triggers 41-60)
│   ├── LEVELS_TEST_GROUP4.DAT        Test group 4 (triggers 61-80)
│   ├── LEVELS_TEST_GROUP5.DAT        Test group 5 (triggers 81-100)
│   └── test_groupN_notes.txt         Notes for each group
│
├── 📂 [zones]/                       Door data by zone (41 JSON files)
│   ├── cavern_of_death/              8 areas
│   ├── forest/                       4 areas
│   ├── castle_of_vamp/               5 areas
│   ├── valley/                       1 area
│   ├── ancient_ruins/                2 areas
│   ├── fire_mountain/                1 area
│   ├── tower/                        6 areas
│   ├── undersea/                     2 areas
│   ├── hall_of_demons/               7 areas
│   └── sealed_cave/                  5 areas
│
└── 📋 Reference files
    ├── door_types_reference.json     7 door types defined
    ├── keys_reference.json           19 keys cataloged
    ├── zone_index.json               Zone/area index
    └── EXAMPLE_area_with_doors.json  Template example
```

## 🚀 Quick Start

### 1. Read Documentation
```
docs/README_START_HERE.txt  ← Start here!
```

### 2. Run Trigger Tests
```bash
cd scripts
py -3 test_triggers_system.py info
```

### 3. Apply Test Patch
```bash
cd ../..  # Back to GameplayPatch root
apply_trigger_test.bat 1
```

## 📊 What's Included

### Analysis Results
- **19 keys/amulets** extracted from BLAZE.ALL
- **7 door types** identified (magic_locked, demon/ghost_engraved, etc.)
- **335 door references** found in game data
- **500 triggers** extracted from LEVELS.DAT

### Door Types
1. `unlocked` - Standard open door
2. `magic_locked` - Requires Magical Key
3. `demon_engraved` - Requires Demon Amulet
4. `ghost_engraved` - Requires Ghost Amulet
5. `key_locked` - Requires specific key
6. `event_locked` - Opens after event
7. `boss_door` - Opens after boss defeat

### Keys & Amulets (19 total)
- **3 Amulets**: Magical Key, Demon Amulet, Ghost Amulet
- **4 Dragon Keys**: Black, Blue, Red, Dragon Key
- **3 Special Keys**: Cell, Cellar, Clearing
- **9 Standard Keys**: Blue, Golden, Moon, Black, Antique, etc.

## 🛠️ Tools

### Scripts (in `scripts/`)

**test_triggers_system.py** - Main trigger testing tool
```bash
py -3 test_triggers_system.py extract      # Extract triggers
py -3 test_triggers_system.py patch N      # Create test patch (N=1-5)
py -3 test_triggers_system.py disable ID   # Disable specific trigger
py -3 test_triggers_system.py info         # Show info
```

**analyze_trigger_format.py** - Analyze trigger binary format
```bash
py -3 analyze_trigger_format.py
```

### Batch Files (in root)

**apply_trigger_test.bat** - Apply test patch to game
```bash
apply_trigger_test.bat 1  # Test group 1
```

**restore_original_levels.bat** - Restore vanilla
```bash
restore_original_levels.bat
```

## 📚 Documentation

| File | Description |
|------|-------------|
| `README_START_HERE.txt` | Quick start guide |
| `ANALYSE_COMPLETE.md` | Full analysis report |
| `TRIGGER_TEST_GUIDE.md` | Testing methodology |
| `EXPLORATION_GUIDE.md` | In-game cataloging |
| `SUMMARY.md` | Visual summary with tables |

## 🎯 Usage Workflows

### Workflow 1: Identify Door Triggers
1. Read `docs/TRIGGER_TEST_GUIDE.md`
2. Apply test: `apply_trigger_test.bat 1`
3. Play game, note which doors disappeared
4. Repeat for groups 2-5
5. Analyze results

### Workflow 2: Catalog Doors In-Game
1. Read `docs/EXPLORATION_GUIDE.md`
2. Explore each zone/area
3. Note door types and positions
4. Fill in JSON files

### Workflow 3: Analyze Triggers
1. `cd scripts`
2. `py -3 analyze_trigger_format.py`
3. Study trigger structure
4. Test hypotheses in-game

## 📈 Statistics

- **73 files** created
- **10 zones** organized
- **41 areas** mapped
- **500 triggers** extracted
- **225 MB** test patches
- **~10,000 lines** of data/docs

## 🔗 Integration

### With Build System
Test patches integrate with main build pipeline:
1. `apply_trigger_test.bat N` → patches LEVELS.DAT
2. Calls `build.bat` → rebuilds BIN
3. Ready to test

### With Version Control
- All analysis data committed to git
- Test patches excluded (too large)
- Regenerate with `py -3 scripts/test_triggers_system.py patch N`

## 💡 Next Steps

1. **Option A**: In-game exploration (recommended)
   - Follow `docs/EXPLORATION_GUIDE.md`
   - Catalog doors manually

2. **Option B**: Trigger testing (advanced)
   - Follow `docs/TRIGGER_TEST_GUIDE.md`
   - Identify door triggers systematically

3. **Option C**: Both approaches
   - Combine manual + automated identification

## 📞 Support

- **Main Documentation**: `docs/README_START_HERE.txt`
- **Trigger Testing**: `docs/TRIGGER_TEST_GUIDE.md`
- **In-Game Guide**: `docs/EXPLORATION_GUIDE.md`
- **Complete Analysis**: `docs/ANALYSE_COMPLETE.md`

---

**Created**: 2026-02-13
**Status**: Ready for testing
**Methodology**: Binary analysis + textual extraction + in-game validation
