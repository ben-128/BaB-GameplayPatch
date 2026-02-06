-- watch_formation_poll.lua
-- Surveille la zone memoire des formations a chaque frame
-- Quand les donnees changent (= zone rechargee), met en pause
--
-- USAGE:
-- 1. Etre dans Forest F1 (formations chargees en RAM)
-- 2. dofile("D:/projets/Bab_Gameplay_Patch/tools/watch_formation_poll.lua")
-- 3. Resume (F5)
-- 4. Va dans une AUTRE zone (Floor 2, ville, etc.)
-- 5. Reviens dans Forest F1
-- 6. Le script detecte le changement et pause le jeu
-- 7. Le PC affiche indique le code en cours d'execution au moment du chargement

print("=== Formation Memory Poller ===")
print("")

local ram_base = 0x80000000
local ptr = PCSX.getMemPtr()

-- Adresse des formations Forest F1 Area1 (trouvee precedemment)
local watch_addr = 0x800E2E58
local watch_off = watch_addr - ram_base
local watch_size = 128  -- Surveiller les 128 premiers bytes (4 records)

-- Prendre le snapshot actuel
local snapshot = {}
for i = 0, watch_size - 1 do
    snapshot[i] = ptr[watch_off + i]
end

print(string.format("Snapshot pris a 0x%08X (%d bytes)", watch_addr, watch_size))

-- Afficher les premiers bytes
local hex = ""
for i = 0, 31 do
    hex = hex .. string.format("%02X ", snapshot[i])
end
print("Premiers 32 bytes: " .. hex)
print("")

-- Compteur de frames
local frame_count = 0
local data_cleared = false
local data_reloaded = false

-- Creer le listener
local listener = PCSX.Events.createEventListener("GPU::Vsync", function()
    frame_count = frame_count + 1

    -- Verifier toutes les 10 frames (pas besoin de chaque frame)
    if frame_count % 10 ~= 0 then return end

    -- Comparer avec le snapshot
    local changed = false
    local all_zero = true

    for i = 0, watch_size - 1 do
        local current = ptr[watch_off + i]
        if current ~= snapshot[i] then
            changed = true
        end
        if current ~= 0 then
            all_zero = false
        end
    end

    if changed and not data_cleared and all_zero then
        -- Les donnees ont ete effacees (zone decharge)
        data_cleared = true
        print(string.format("[Frame %d] Donnees EFFACEES a 0x%08X (zone dechargee)", frame_count, watch_addr))
        print("En attente du rechargement...")
    end

    if changed and data_cleared and not all_zero then
        -- Les donnees ont ete RE-ECRITES (zone rechargee)
        data_reloaded = true
        print(string.format("[Frame %d] Donnees RECHARGEES a 0x%08X!", frame_count, watch_addr))
        print("")

        -- PAUSE!
        PCSX.pauseEmulator()

        -- Afficher l'etat
        local regs = PCSX.getRegisters()
        if regs then
            print("=== REGISTRES AU MOMENT DE LA PAUSE ===")
            local reg_names = {"zero","at","v0","v1","a0","a1","a2","a3",
                               "t0","t1","t2","t3","t4","t5","t6","t7",
                               "s0","s1","s2","s3","s4","s5","s6","s7",
                               "t8","t9","k0","k1","gp","sp","fp","ra"}
            for idx = 0, 31 do
                local name = reg_names[idx + 1]
                if regs.GPR and regs.GPR[idx] then
                    print(string.format("  $%-4s = 0x%08X", name, regs.GPR[idx]))
                end
            end
            if regs.pc then
                print(string.format("  PC    = 0x%08X", regs.pc))
            end
            if regs.lo then print(string.format("  LO    = 0x%08X", regs.lo)) end
            if regs.hi then print(string.format("  HI    = 0x%08X", regs.hi)) end
        else
            print("getRegisters() n'a pas retourne de donnees")
        end

        -- Afficher les nouvelles donnees
        print("")
        print("Nouvelles donnees a 0x" .. string.format("%08X", watch_addr) .. ":")
        hex = ""
        for i = 0, 31 do
            hex = hex .. string.format("%02X ", ptr[watch_off + i])
        end
        print("  " .. hex)

        -- Desactiver le listener
        print("")
        print("=== PAUSE - Ouvre Debug > Show Assembly pour voir le code ===")
        print("Note le PC et regarde le desassemblage autour.")
        print("Le code actuellement en cours est PROCHE du code de chargement.")
        return
    end

    -- Si les donnees changent sans etre effacees d'abord
    if changed and not data_cleared and not all_zero then
        data_reloaded = true
        print(string.format("[Frame %d] Donnees MODIFIEES a 0x%08X (rechargement direct)", frame_count, watch_addr))

        PCSX.pauseEmulator()

        local regs = PCSX.getRegisters()
        if regs then
            print("=== REGISTRES ===")
            if regs.pc then
                print(string.format("  PC = 0x%08X", regs.pc))
            end
            if regs.GPR then
                local reg_names = {"zero","at","v0","v1","a0","a1","a2","a3",
                                   "t0","t1","t2","t3","t4","t5","t6","t7",
                                   "s0","s1","s2","s3","s4","s5","s6","s7",
                                   "t8","t9","k0","k1","gp","sp","fp","ra"}
                for idx = 0, 31 do
                    local name = reg_names[idx + 1]
                    if regs.GPR[idx] then
                        local val = regs.GPR[idx]
                        if val ~= 0 then
                            print(string.format("  $%-4s = 0x%08X", name, val))
                        end
                    end
                end
            end
        end

        print("")
        hex = ""
        for i = 0, 31 do
            hex = hex .. string.format("%02X ", ptr[watch_off + i])
        end
        print("Nouvelles donnees: " .. hex)
        print("")
        print("=== Ouvre Debug > Show Assembly ===")
        return
    end
end)

print("Listener actif sur GPU::Vsync")
print("Resume le jeu (F5), change de zone, puis reviens dans Forest F1.")
print("Le script pausera automatiquement quand les formations seront rechargees.")
print("")
print("Pour annuler: ferme et reouvre la console Lua")
