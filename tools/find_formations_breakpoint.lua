-- find_formations_breakpoint.lua
-- Script pour PCSX-Redux: cherche les formation templates en RAM et pose un breakpoint
--
-- Usage dans PCSX-Redux:
--   1. Charger le jeu, aller dans Forest Floor 1
--   2. Menu Debug > Show Lua Console
--   3. Coller ce script ou faire: dofile("D:/projets/Bab_Gameplay_Patch/tools/find_formations_breakpoint.lua")

print("=== Formation Template Finder ===")
print("")

-- Pattern: premier record de formation (Forest F1 Area1)
-- byte[0:4]=00000000 byte[4:8]=FFFFFFFF byte[8]=00(slot0) byte[9]=FF(marker)
-- On cherche: 00 00 00 00 FF FF FF FF xx FF 00 00
-- Le xx est le slot index (0, 1, ou 2)

-- Aussi essayer le pattern Cavern F1 Area1 avec area_id DC01
-- byte[24:26] = DC 01, byte[26:32] = FF FF FF FF FF FF

local ram_base = 0x80000000
local ram_size = 2 * 1024 * 1024  -- 2 MB

-- Lire un byte depuis la RAM PSX
local function read_byte(addr)
    return PCSX.getMemPtr()[addr - ram_base]
end

-- Lire 4 bytes LE depuis la RAM PSX
local function read_u32(addr)
    local ptr = PCSX.getMemPtr()
    local off = addr - ram_base
    return ptr[off] + ptr[off+1] * 256 + ptr[off+2] * 65536 + ptr[off+3] * 16777216
end

-- Cherche le pattern formation dans toute la RAM
local function search_formation_pattern()
    local ptr = PCSX.getMemPtr()
    local found = {}

    print("Recherche du pattern formation en RAM (2 Mo)...")
    print("Pattern: 00000000 FFFFFFFF xx FF 0000 ... areaID FFFFFFFFFFFF")
    print("")

    for i = 0, ram_size - 32 do
        -- Check byte[0:4] = 00 00 00 00
        if ptr[i] == 0 and ptr[i+1] == 0 and ptr[i+2] == 0 and ptr[i+3] == 0 then
            -- Check byte[4:8] = FF FF FF FF
            if ptr[i+4] == 0xFF and ptr[i+5] == 0xFF and ptr[i+6] == 0xFF and ptr[i+7] == 0xFF then
                -- Check byte[9] = FF (template marker)
                if ptr[i+9] == 0xFF then
                    -- Check byte[26:32] = FF FF FF FF FF FF (terminator)
                    if ptr[i+26] == 0xFF and ptr[i+27] == 0xFF and ptr[i+28] == 0xFF
                       and ptr[i+29] == 0xFF and ptr[i+30] == 0xFF and ptr[i+31] == 0xFF then
                        -- C'est un formation record!
                        local addr = ram_base + i
                        local slot = ptr[i+8]
                        local area_lo = ptr[i+24]
                        local area_hi = ptr[i+25]
                        local area_id = string.format("%02x%02x", area_lo, area_hi)

                        -- Verifier que c'est le PREMIER record d'une zone
                        -- (pas un continuation record qui a aussi 00000000 en prefix)
                        -- Le premier record a byte[4:8]=FFFFFFFF, c'est deja verifie
                        -- Mais on veut le premier de la ZONE (pas juste d'une formation)
                        -- On check si le byte AVANT ce record n'est pas un suffix
                        local is_first_in_zone = true
                        if i >= 4 then
                            -- Si les 4 bytes avant sont un suffix, c'est pas le premier
                            -- Difficile a determiner, on liste tout
                        end

                        table.insert(found, {
                            addr = addr,
                            slot = slot,
                            area_id = area_id
                        })
                    end
                end
            end
        end
    end

    return found
end

-- Groupe les resultats par area_id
local function group_by_area(results)
    local areas = {}
    for _, r in ipairs(results) do
        if not areas[r.area_id] then
            areas[r.area_id] = {first_addr = r.addr, count = 0, records = {}}
        end
        areas[r.area_id].count = areas[r.area_id].count + 1
        table.insert(areas[r.area_id].records, r)
    end
    return areas
end

-- Execution
local results = search_formation_pattern()

if #results == 0 then
    print("Aucun formation record trouve en RAM!")
    print("Es-tu bien dans une zone avec des monstres (Forest, Cavern, etc.) ?")
    print("Le jeu doit avoir charge la zone pour que les donnees soient en RAM.")
else
    print(string.format("Trouve %d formation-start records:", #results))
    print("")

    local areas = group_by_area(results)

    -- Affiche par area_id
    for area_id, info in pairs(areas) do
        print(string.format("  Area ID %s: %d formations, premier record a 0x%08X",
            area_id, info.count, info.first_addr))

        -- Affiche les premiers records
        for j, r in ipairs(info.records) do
            if j <= 10 then
                print(string.format("    F%02d: 0x%08X (slot=%d)", j-1, r.addr, r.slot))
            end
        end
        if info.count > 10 then
            print(string.format("    ... et %d de plus", info.count - 10))
        end
    end

    print("")
    print("=== BREAKPOINTS ===")
    print("Pour trouver le parseur, pose un breakpoint READ sur le premier record.")
    print("Dans Debug > Breakpoints, ajouter:")

    -- On montre le breakpoint pour chaque area trouvee
    for area_id, info in pairs(areas) do
        local addr = info.first_addr
        print(string.format("  Address: 0x%08X  Type: Read  Size: 4  (area %s)", addr + 4, area_id))
        print(string.format("  -> Lit byte[4:8] (le delimiteur FFFFFFFF) du premier record"))
    end

    print("")
    print("Quand le breakpoint se declenche:")
    print("  1. Note l'adresse PC (Program Counter)")
    print("  2. Note les registres (surtout ceux avec des adresses 0x80xxxxxx)")
    print("  3. Step (F11) quelques instructions pour voir la boucle")
    print("  4. Copie-moi le desassemblage autour du PC")
end

print("")
print("=== Done ===")
