================================================================================
                    MONSTER STATS - Bab Gameplay Patch
================================================================================

SOURCE FILE: BLAZE.ALL (in extract folder)
TOTAL MONSTERS FOUND: 118

================================================================================
DATA STRUCTURE (per monster entry)
================================================================================

Each monster entry has the following structure:

Offset  Size    Field               Description
------  ----    -----               -----------
0x00    16      Name                Monster name (null-terminated, padded)
0x10    2       exp_reward          Experience points reward
0x12    2       stat2_unknown       Unknown
0x14    2       hp                  Hit Points
0x16    2       stat4_magic         Magic power / Mana
0x18    2       stat5_randomness    Damage randomness (dealt and received)
0x1A    2       stat6_collider_type Collider type / Hitbox shape
0x1C    2       stat7_death_fx_size Death FX size
0x1E    2       stat8_unknown       Unknown (family/AI related?)
0x20    2       stat9_collider_size Collider/Hitbox size
0x22    2       stat10_drop_rate    Loot/Drop rate
0x24    2       stat11_creature_type  Creature type flags (bitfield, see below)
0x26    2       stat12_flags        Flags/abilities (bitfield)
0x28    2       stat13_flags        Flags/abilities (bitfield)
0x2A    2       stat14_flags        Flags/abilities (bitfield)
0x2C    2       stat15_flags        Flags/abilities (bitfield)
0x2E    2       stat16_atk1         Attack stat 1
0x30    2       stat17_def1         Defense/Resist 1
0x32    2       stat18_atk2         Attack stat 2
0x34    2       stat19_def2         Defense/Resist 2
0x36    2       stat20_atk3         Attack stat 3
0x38    2       stat21_def3         Defense/Resist 3
0x3A    2       stat22_atk4         Attack stat 4
0x3C    2       stat23_def4         Defense/Resist 4

Entry size: 96 bytes (0x60) - name (16) + stats (46) + padding (34)

================================================================================
STAT HYPOTHESES (based on data analysis)
================================================================================

stat4 - MAGIC POWER / MANA
  - Mages have high values: Arch-Magi (215), Dark-Wizard (840), Efreet (807)
  - Bosses have very high values: Budgietom (1600), Dark-Angel (1400)
  - Physical monsters have low values: Goblin (8)

stat5 - DAMAGE RANDOMNESS
  - Adds randomness to both damage dealt and damage received
  - Higher value = more variance in combat damage

stat6 - COLLIDER TYPE / HITBOX
  - Defines the collision/hitbox shape of the monster
  - Observed values:
      0  = Standard (most common)
      1  = Armored/Large (Black-Knight, Born-Golem, Cave-Scissors)
      2  = Flying (Giant-Bat, King-Mummy)
      3  = Humanoid (Dark-Magi, Dark-Goblin, Cave-Bear)
      4  = Small/Insect (Killer-Bee, Goblin-Fly)
      5  = Quadruped (Wolf, Silver-Wolf, Winter-Wolf)
      6  = Hell-Hound only
      8  = Vampire-Bat only
      10 = Sphere (Metal-Ball, Metal-Slime)
      15 = Snake (Viper)
      20 = Evil-Ball only
      30 = Skeleton
      52 = Blood-Skeleton
      140 = Salamander

stat7 - DEATH FX SIZE
  - Controls the size of the death effect/explosion
  - Confirmed through testing

stat8 - UNKNOWN
  - Monsters of the same family share the same value
  - Possibly AI behavior, animations, or sound sets
  - Examples of family groupings:
      15 = Snakes (Big-Viper, Giant-Snake)
      35 = Bats (Giant-Bat, Vampire-Bat)
      64 = Slimes (all slimes)
      75 = Wolves (Wolf, Silver-Wolf, Winter-Wolf)
     110 = Goblins (all goblins)
     155 = Mummies (all mummies)

stat9 - COLLIDER / HITBOX SIZE
  - Controls the size of the monster's collision hitbox
  - Confirmed through testing

stat10 - DROP RATE / LOOT RATE
  - Controls how often the monster drops items
  - Confirmed through testing

stat11 - CREATURE TYPE FLAGS (bitfield)
  - 0x0002 = Mythical beast (Chimera, Griffin, Gorgon, Harpy)
  - 0x0004 = Giant (Ogre, Giant, Green-Giant)
  - 0x0008 = Construct (Golem, Gargoyle, Evil-Crystal)
  - 0x0010 = Animal (Bear, Bat, Snake)
  - 0x0080 = Dragon (Red-Dragon, Wyvern, Zombie-Dragon)
  - 0x0100 = Undead (Zombie, Skeleton, Vampire, Mummy, Ghost)
  - 0x0200 = Incorporeal (Ghost, Wraith, Wight)
  - 0x0400 = Lycanthrope (Werewolf, Weretiger)
  - 0x0800 = Slime/Amorphous (all Slimes)
  - 0x8000 = Boss/Large creature

stat12-15 - FLAGS / ABILITIES (bitfields)
  - Additional creature flags and abilities
  - Exact meaning unknown

stat16-23 - COMBAT STATS (4 pairs of ATK/DEF)
  - Even stats [16,18,20,22] = Attack/Offensive power
  - Odd stats [17,19,21,23] = Defense/Resistance
  - Offensive monsters (Behemoth, Troll, Giant): high even stats
  - Defensive monsters (Metal-Slime, Metal-Ball): high odd stats
  - Metal-Slime: 298 atk total, 1310 def total (very defensive)
  - Behemoth: 462 atk total, 376 def total (offensive)
  - Values range 0-500
  - Most common range: 60-66 for weak monsters
  - Budgietom: 0 (final boss, no drops?)
  - Red-Dragon: 500 (rare drops or high resistance?)

================================================================================
HOW TO MODIFY VALUES
================================================================================

1. Open BLAZE.ALL in a hex editor (HxD, 010 Editor, etc.)
2. Go to the offset specified in each monster's JSON file
3. Values are stored as 16-bit little-endian integers
   Example: HP of 4400 = 0x1130 = stored as "30 11"
4. Modify the bytes and save
5. Rebuild the game ISO with modified BLAZE.ALL

================================================================================
COMPLETE MONSTER LIST (118 monsters, sorted by HP)
================================================================================

Monster                  HP    EXP   st2   Offset
-------                  --    ---   ---   ------
Giant-Ant               12     2    20   0x148C244
Goblin-Wizard           12   103     2   0x2BEF2A8
Wing-Fish               12     4    50   0x1498398
Kobold                  14     2     1   0x1490a10
Viper                   18    80    14   0xF8625C
Giant-Club              21     5    45   0x1490b30
Killer-Bee              26     9    16   0x14a2228
Giant-Snake             30     8     5   0x1494198
Giant-Spider            32    30    37   0xf87b24
Goblin-Shaman           33    16     3   0x1498278
Goblin                  33    16     2   0x1498218
Giant-Bat               36    15     4   0xf861f8
Killer-Bear             36    18     6   0x149ba84
Lizard-Man              39    30    19   0x197c2e4
Barricade               40     1     0   0x14981B8
Giant-Scorpion          44    25    10   0xf87a04
Goblin-Fly              46    30    60   0x197625c
Giant-Centipede         51    29    12   0xF87A64
Skeleton                52    71    40   0x2414a3a
Green-Slime             60    32     7   0x197c284
Wolf                    60    38    35   0x2514a44
Goblin-Leader           62    36    63   0xf81ac0
Spirit-Ball             69    87    41   0x2bf1acc
Gargoyle                71    38    21   0x2514984
Big-Viper               80    18     5   0xf86258
Dark-Magi               80    48    22   0x197619c
Living-Sword            80    80    26   0x1985ad4
Silver-Wolf             80    38    35   0x2417ab8
Will-O-The-Wisp         80    67    41   0x14afa48
Winter-Wolf             80    42    35   0x25D09D4
Cave-Bear               81    54     6   0xf911a0
Killer-Fish             81    68    50   0xF8B200
Dark-Goblin             82   103     2   0x2bef248
Salamander              82   240   220   0x2bff2a0
Ghost                   84    58    31   0x2416190
Blue-Slime              85    61     7   0xf91200
Cave-Scissors           88    82    45   0xf8ca7c
Red-Slime               90    53     7   0x1deb2d8
Zombie                  90    35    27   0x240d9b0
Snow-Bear               92    50     6   0x25D0974
Shadow                  93    85    39   0x242d23c
Crimson-Lizard         101    34    19   0x197c3a4
Harpy                  103    56    51   0x2417a58
Wraith                 105    67    30   0x1deb278
Vampire-Bat            106    76     4   0x241AAC8
Ghoul                  120    48    28   0x1de8210
Revenant               120   100    33   0x1df5304
Hippogriff             121    65    52   0x25d2958
Marble-Gargoyle        121    80    21   0x2421194
Trent                  121    65    15   0x14af988
Yellow-Slime           125    91     7   0x1DF5364
Living-Armor           131    91    40   0x1985b34
Wight                  132    53    36   0x1de81b0
Lesser-Vampire         136    89    34   0x242d29c
Evil-Stalker           137   112    24   0x2bf4a64
Stalker                137    86    24   0x1985a14
Blood-Shadow           140   102    39   0x2bf4a04
Noble-Mummy            140    96    29   0x1DF53C4
Poison-Flower          140    50    17   0x14aa260
Blood-Skeleton         141    62    32   0x2414a34
Mummy                  142    78    29   0x1df52a4
Desert-Lizard          150    81    58   0x14B316C
Black-Knight           151    87    25   0x1985a74
Gremlin                156   110    60   0x2bff17c
Vampire                156    98    34   0x242d1dc
Black-Lizard           159    85    19   0x269e1a4
Arch-Magi              160    98    22   0x199b228
Wyrm                   162    86    53   0x269e204
Hell-Hound             178   157    61   0x2c071e4
Hell-Harpy             180   120    51   0x2BEF188
Blood-Mummy            190    95    29   0x1DEB218
Red-Knight             190    86    38   0x242d17c
Succubus               190   165    62   0x2c08a34
Metal-Ball             200    87    41   0x25149E4
Gray-Arm               202   116    53   0x2c08974
Basirisk               207   151    58   0x2BFC1F0
Chimera                210   103    42   0x2517158
Undead-Knight          215    88    38   0x1df51e4
Metal-Slime            225   140     7   0x25171B8
Guard-Golem            231    26    40   0x196E2C8
Death-Knight           240   121    38   0x2bf1a0c
Ice-Salamander         240   168     9   0x2BFF29C
King-Mummy             240   126    29   0x1DF5424
Kraken-Foot            300    90    83   0x269e2c4
OwlBear                300    38    68   0x14A21C8
Ogre                   315    96    57   0xf93270
Giant                  320    95    14   0x14B322C
Hell-Ogre              320   160    57   0x2c089d4
Born-Golem             326    99    23   0x19819F0
Gorgon                 326   165    59   0x2C07244
Hard-Born              326   110    23   0x199b288
Black-Durahan          358   110    74   0x1DF99A0
Shadow-Demon           360   100    93   0x199524C
Green-Giant            400   100    14   0xF931B0
Kraken-Hand            400    90    82   0x269e264
Platinum-Knight        400   120    25   0x199518C
Werewolf               468    85    77   0x2417998
Weretiger              500    85    78   0x24179F8
Evil-Ball              519   157    41   0x2BF7220
Dark-Elf               563   100    71   0x198a9fc
Dragon-Puppy           700    40    65   0xF87AC4
Wyvern                 700    96    72   0x198AA5C
Durahan                808    80    74   0x1DE8270
Vampire-Lord           840   150    79   0x24339dc
Troll                  850   130    64   0xF932D0
Evil-Crystal           900   255     0   0x1991ba8
Dark-Wizard            910   140    73   0x19951ec
Griffin               1030   180    85   0x25D29B8
Undead-Master         1350   150    75   0x1DF9A00
Carberos              2100   200    89   0x2C07184
Behemoth              2160   150    70   0x14B794C
Greater-Demon         2300   218    93   0x2C0B954
Dark-Angel            2391   238    99   0x2c0d954
Efreet                2400   212    66   0x2C0A954
Demon-Lord            2763   235    98   0x2C0C954
Budgietom             3000   320   100   0x2C0E944
Zombie-Dragon         4400   180    88   0x2BF71C0
Red-Dragon            8000   306    67   0x102E1F8

================================================================================
BOSS MONSTERS (HP >= 1000)
================================================================================

Red-Dragon       HP:  8000  EXP: 306  st2:  67
Zombie-Dragon    HP:  4400  EXP: 180  st2:  88
Budgietom        HP:  3000  EXP: 320  st2: 100
Demon-Lord       HP:  2763  EXP: 235  st2:  98
Efreet           HP:  2400  EXP: 212  st2:  66
Dark-Angel       HP:  2391  EXP: 238  st2:  99
Greater-Demon    HP:  2300  EXP: 218  st2:  93
Behemoth         HP:  2160  EXP: 150  st2:  70
Carberos         HP:  2100  EXP: 200  st2:  89
Undead-Master    HP:  1350  EXP: 150  st2:  75
Griffin          HP:  1030  EXP: 180  st2:  85

================================================================================
NOTE: Harbinger
================================================================================

"Harbinger" is mentioned in game dialogues as "the greatest infernal machine"
but does NOT appear as a standard monster entry. It may be:
- A story element only (not fightable)
- Stored in a different data format
- Have a different internal name

================================================================================
Generated by analysis of BLAZE.ALL from PS1 game (SLES_008.45)
================================================================================
