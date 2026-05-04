%Clean up function for aud pause
function CleanupFunctionAutoSeq(f, filepath, name)
SaveBpodSessionData; % Saves the field BpodSystem.Data to the current data file
disp('Data saved');
%save figure at the end of the session
figure(f);
savefig([filepath '\' name '.fig']);
close(f);
disp('Figure saved')

SaveTrainingLevel
disp('Training Level Saved')

% save_Trial_Settings_HMV(pathToSave, setToSave);
% disp('Settings saved')
clear A

