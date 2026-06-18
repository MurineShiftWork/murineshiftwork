function value = FindValveState(port)

if port == 1
    value = 1;
elseif port == 2
    value = 2;
elseif port == 3
    value = 4;
elseif port == 4
    value = 8;
elseif port == 5
    value = 16;
elseif port == 6
    value = 32;
elseif port == 7
    value = 64;
elseif port == 8
    value = 128;
end

end
