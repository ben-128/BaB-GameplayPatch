-- dump_ram.lua
-- Dump les 2 Mo de RAM PSX dans un fichier
--
-- Usage:
--   1. Pause le jeu (F5)
--   2. dofile("D:/projets/Bab_Gameplay_Patch/tools/dump_ram.lua")
--   3. Le fichier est ecrit dans output/

print("=== RAM Dumper ===")

local ptr = PCSX.getMemPtr()
local ram_size = 2 * 1024 * 1024  -- 2 Mo

-- Determiner le nom du fichier
-- Utilise un compteur simple
local base_path = "D:/projets/Bab_Gameplay_Patch/output/"

-- Chercher quel dump faire
local dump_num = 1
local f1 = io.open(base_path .. "ram_before.bin", "rb")
if f1 then
    f1:close()
    dump_num = 2
end

local filename
if dump_num == 1 then
    filename = base_path .. "ram_before.bin"
    print("Dump 1/2 : AVANT entree dans la zone")
else
    filename = base_path .. "ram_after.bin"
    print("Dump 2/2 : APRES entree dans la zone")
end

-- Lire la RAM et ecrire dans le fichier
print(string.format("Ecriture de %d bytes dans %s ...", ram_size, filename))

local out = io.open(filename, "wb")
if not out then
    print("ERREUR: impossible d'ouvrir " .. filename)
    return
end

-- Ecrire par blocs de 4096
local block_size = 4096
for offset = 0, ram_size - 1, block_size do
    local chunk = {}
    for i = 0, block_size - 1 do
        chunk[i + 1] = string.char(ptr[offset + i])
    end
    out:write(table.concat(chunk))
end

out:close()
print("OK! Fichier ecrit: " .. filename)
print("")

if dump_num == 1 then
    print("=== Prochaine etape ===")
    print("1. Resume le jeu (F5)")
    print("2. Entre dans Forest Floor 1 (ou la zone cible)")
    print("3. Pause le jeu")
    print("4. Re-lance ce script:")
    print('   dofile("D:/projets/Bab_Gameplay_Patch/tools/dump_ram.lua")')
    print("5. Ca va creer ram_after.bin")
    print("6. Dis-moi quand c'est fait, je ferai le diff")
else
    print("=== Les 2 dumps sont prets! ===")
    print("Dis-moi et je lance le diff pour trouver le code de formation.")
end
