-- watch_formations.lua
-- Surveille la zone memoire des formations et detecte quand elle change
-- + Pose des breakpoints Execute sur du code connu
--
-- dofile("D:/projets/Bab_Gameplay_Patch/tools/watch_formations.lua")

print("=== Formation Memory Watcher ===")
print("")

-- D'abord, lister ce qu'il y a dans PCSX.Events
print("Events disponibles:")
if PCSX.Events then
    for k, v in pairs(PCSX.Events) do
        print(string.format("  PCSX.Events.%s = %s", k, type(v)))
    end
end
print("")

-- Lister PCSX.CONSTS
print("Constants disponibles:")
if PCSX.CONSTS then
    for k, v in pairs(PCSX.CONSTS) do
        print(string.format("  PCSX.CONSTS.%s = %s (%s)", k, tostring(v), type(v)))
    end
end
print("")

-- Essai: addBreakpoint avec des constantes de type
print("Test breakpoint avec CONSTS...")
if PCSX.CONSTS then
    for k, v in pairs(PCSX.CONSTS) do
        if type(v) == "number" then
            local ok, err = pcall(function()
                -- Essayer d'ajouter un breakpoint avec cette constante comme type
                PCSX.addBreakpoint(0x800E2E58, v, 4)
            end)
            if ok then
                print(string.format("  SUCCES: PCSX.addBreakpoint(addr, CONSTS.%s, 4)", k))
            end
        end
    end

    -- Essai avec 4 args
    for k, v in pairs(PCSX.CONSTS) do
        if type(v) == "number" then
            local ok, err = pcall(function()
                PCSX.addBreakpoint(0x800E2E58, v, 4, "read")
            end)
            if ok then
                print(string.format("  SUCCES 4args: PCSX.addBreakpoint(addr, CONSTS.%s, 4, 'read')", k))
            end
        end
    end
end
print("")

-- Pose des breakpoints EXECUTE sur du code connu dans l'exe
-- Ces fonctions sont appelees lors du traitement des formations
local code_breakpoints = {
    {addr = 0x80029F60, name = "Formation buffer init"},
    {addr = 0x80017604, name = "Formation count table read"},
    {addr = 0x800176CC, name = "Packed bitfield decode"},
}

print("Breakpoints Execute poses:")
for _, bp in ipairs(code_breakpoints) do
    local ok, err = pcall(function()
        PCSX.addBreakpoint(bp.addr)
    end)
    if ok then
        print(string.format("  0x%08X : %s", bp.addr, bp.name))
    else
        print(string.format("  0x%08X : ERREUR - %s", bp.addr, tostring(err)))
    end
end
print("")

-- Snapshot des 32 premiers bytes de la formation area
local ptr = PCSX.getMemPtr()
local base = 0x800E2E58 - 0x80000000
local snapshot = {}
for i = 0, 31 do
    snapshot[i] = ptr[base + i]
end

local function hex_dump(off, len)
    local s = ""
    for i = 0, len - 1 do
        s = s .. string.format("%02X ", ptr[off + i])
    end
    return s
end

print("Snapshot actuel de 0x800E2E58 (32 bytes):")
print("  " .. hex_dump(base, 32))
print("")

print("=== INSTRUCTIONS ===")
print("1. Resume le jeu (F5)")
print("2. Va dans une autre zone puis reviens dans Forest F1")
print("3. Si un breakpoint Execute se declenche:")
print("   -> Note le PC et les registres")
print("   -> Step (F11) pour voir ce que fait le code")
print("   -> Copie le desassemblage visible dans le debugger")
print("")
print("Si aucun breakpoint ne se declenche apres re-entree dans Forest:")
print("   -> Le code de parsing n'est PAS dans les fonctions qu'on a trouvees")
print("   -> On devra chercher ailleurs dans l'exe")
