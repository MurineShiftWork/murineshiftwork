function structure = make_block_structure(input_arg,Lower_range,Upper_Range,MaxTrials)

structure = ones(1,randi([Lower_range Upper_Range],1));
if input_arg == 2
    while length(structure) < MaxTrials
        structure = cat(2,structure,ones(1,randi([Lower_range Upper_Range],1))*2);
        structure = cat(2,structure,ones(1,randi([Lower_range Upper_Range],1)));
    end
elseif input_arg == 3
    while length(structure) < MaxTrials
        structure = cat(2,structure,ones(1,randi([Lower_range Upper_Range],1))*3);
        structure = cat(2,structure,ones(1,randi([Lower_range Upper_Range],1))*2);
        structure = cat(2,structure,ones(1,randi([Lower_range Upper_Range],1)));
    end
end
end

