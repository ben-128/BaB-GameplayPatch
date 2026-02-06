-- breakpoint_formations.lua
-- Pose un breakpoint READ via l'API Lua de PCSX-Redux
-- Plus fiable que l'interface graphique
--
-- Usage: dofile("D:/projets/Bab_Gameplay_Patch/tools/breakpoint_formations.lua")

print("=== Setting formation read breakpoint ===")

-- Adresse du premier record de formation Forest F1 Area1
-- (trouvee par le script precedent)
local target = 0x800E2E58

-- Methode 1: Breakpoint via PCSX.addBreakpoint (si disponible)
if PCSX.addBreakpoint then
    PCSX.addBreakpoint(target, 4, "Read")
    print(string.format("Breakpoint READ pose a 0x%08X (via addBreakpoint)", target))
elseif PCSX.pauseOnRead then
    PCSX.pauseOnRead(target)
    print(string.format("Breakpoint READ pose a 0x%08X (via pauseOnRead)", target))
else
    print("API breakpoint non trouvee. Essayons une autre methode...")
end

-- Methode 2: Polling - verifie periodiquement si les donnees changent
-- Cela nous permet de detecter quand la zone est rechargee
print("")
print("Methode alternative: surveillance par polling")
print("On va surveiller l'adresse et detecter quand les donnees changent")
print("")

local ptr = PCSX.getMemPtr()
local off = target - 0x80000000

-- Lire les 32 premiers bytes actuels
local current = {}
for i = 0, 31 do
    current[i] = ptr[off + i]
end

print(string.format("Contenu actuel a 0x%08X:", target))
local hex = ""
for i = 0, 31 do
    hex = hex .. string.format("%02X ", current[i])
    if i == 15 then hex = hex .. "\n    " end
end
print("    " .. hex)

-- Verifier si c'est bien un formation record
if current[4] == 0xFF and current[5] == 0xFF and current[6] == 0xFF and current[7] == 0xFF
   and current[9] == 0xFF then
    print("-> C'est bien un formation record (FFFFFFFF delimiter + FF marker)")
    print(string.format("   Slot: %d, Area ID: %02X%02X", current[8], current[24], current[25]))
else
    print("-> ATTENTION: ce n'est PAS un formation record valide!")
    print("   Les donnees ont peut-etre ete ecrasees ou la zone a change.")
    print("   Re-lance find_formations_breakpoint.lua apres etre entre dans Forest F1.")
end

print("")
print("=== Instructions ===")
print("1. Desactive les breakpoints manuels (ils peuvent interferer)")
print("2. Va dans une AUTRE zone (ville, floor 2, etc.)")
print("3. Execute ce script pour poser le breakpoint:")
print('   dofile("D:/projets/Bab_Gameplay_Patch/tools/breakpoint_formations.lua")')
print("4. Resume le jeu (F5)")
print("5. Re-entre dans Forest Floor 1")
print("6. Si le breakpoint fonctionne, le jeu va se mettre en pause")
print("   et le debugger va s'ouvrir sur le code de parsing")
print("")
print("Si le breakpoint ne se declenche pas:")
print("  -> Les read breakpoints ne marchent peut-etre pas dans cette version")
print("  -> Essaie un WRITE breakpoint a la place (pour capter le chargement)")
print("  -> Ou utilise Debug > Show CPU (pour breakpoints via le debugger ASM)")
