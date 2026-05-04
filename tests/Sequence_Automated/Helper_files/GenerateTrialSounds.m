function BGSoundTrial = GenerateTrialSounds(SF, BGSound, Pattern, PauseDelay) 

PatternStart = (PauseDelay - 2)*SF;
PatternStart = round(PatternStart); % round to the nearest soundframe
BGSoundTrial = BGSound(PatternStart:((PatternStart-1)+(length(Pattern)))) + Pattern(1,:);

