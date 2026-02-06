-- bp_probe.lua : teste les differents formats de breakpoint dans PCSX-Redux
print("=== Probing PCSX.addBreakpoint API ===")
print("")

local target = 0x800E2E58

-- Essai de differents formats de type
local types_to_try = {
    "read", "Read", "READ",
    "write", "Write", "WRITE",
    "exec", "Exec", "EXEC",
    "Execute", "execute",
    "r", "w", "x",
    "BR1", "BR2", "BR4",
    1, 2, 4,
    0, 3,
}

for _, t in ipairs(types_to_try) do
    local ok, err = pcall(function()
        PCSX.addBreakpoint(target, 4, t)
    end)
    if ok then
        print(string.format("  SUCCESS with type = %s (%s)", tostring(t), type(t)))
    end
end

-- Aussi essayer avec 2 arguments seulement
local ok2, err2 = pcall(function()
    PCSX.addBreakpoint(target, 4)
end)
if ok2 then
    print("  SUCCESS with 2 args only (target, size)")
end

-- Essayer avec un seul argument
local ok1, err1 = pcall(function()
    PCSX.addBreakpoint(target)
end)
if ok1 then
    print("  SUCCESS with 1 arg only (target)")
end

-- Lister les methodes disponibles dans PCSX
print("")
print("=== Methodes disponibles dans PCSX ===")
for k, v in pairs(PCSX) do
    if type(v) == "function" then
        print(string.format("  PCSX.%s = function", k))
    elseif type(v) == "table" then
        print(string.format("  PCSX.%s = table", k))
    elseif type(v) == "string" or type(v) == "number" then
        print(string.format("  PCSX.%s = %s", k, tostring(v)))
    end
end

print("")
print("=== Done ===")
