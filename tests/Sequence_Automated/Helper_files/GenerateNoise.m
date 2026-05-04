% AudPause Helper function for generating bandfiltered noise of defferent frequency spectra
% Based on open source work by Hristo Zhivomirov 07/30/13 
% Emmett Thompson
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

function y = GenerateNoise(m,n,Argument)

if Argument == 1 %Red
    y = rednoise(m,n);
elseif Argument == 2 %Pink
    y = pinknoise(m,n);
elseif Argument == 3 %Violet
    y = violetnoise(m,n);
elseif Argument == 4 %Blue
    y = bluenoise(m,n);
end

    function y = pinknoise(m, n)
        % function: y = pinknoise(m, n)
        % m - number of matrix rows
        % n - number of matrix columns
        % y - matrix with pink (flicker) noise samples
        %     with mu = 0 and sigma = 1 (columnwise)
        % The function generates a matrix of pink (flicker) noise samples
        % (columnwise). In terms of power at a constant bandwidth, pink
        % noise falls off at 3 dB/oct, i.e. 10 dB/dec.
        % difine the length of the noise vector and ensure
        % that M is even, this will simplify the processing
        m = round(m); n = round(n); N = m*n;
        if rem(N, 2)
            M = N+1;
        else
            M = N;
        end
        % generate white noise sequence
        x = randn(1, M)*0.1;
        % FFT
        X = fft(x);
        % prepare a vector with frequency indexes
        NumUniquePts = M/2 + 1;     % number of the unique fft points
        k = 1:NumUniquePts;         % vector with frequency indexes
        % manipulate the left half of the spectrum so the PSD
        % is proportional to the frequency by a factor of 1/f,
        % i.e. the amplitudes are proportional to 1/sqrt(f)
        X = X(1:NumUniquePts);
        X = X./sqrt(k);
        % prepare the right half of the spectrum - a conjugate copy of the left
        % one except the DC component and the Nyquist component - they are unique,
        % and reconstruct the whole spectrum
        X = [X conj(X(end-1:-1:2))];
        % IFFT
        y = real(ifft(X));
        % ensure that the length of y is N
        y = y(1, 1:N);
        % form the noise matrix and ensure unity standard
        % deviation and zero mean value (columnwise)
        y = reshape(y, [m, n]);
        y = bsxfun(@minus, y, mean(y));
        y = bsxfun(@rdivide, y, std(y));
    end


    function y = rednoise(m, n)
        % function: y = rednoise(m, n)
        % m - number of matrix rows
        % n - number of matrix columns
        % y - matrix with red (Brownian) noise samples
        %     with mu = 0 and sigma = 1 (columnwise)
        % The function generates a matrix of red (Brownian) noise samples
        % (columnwise). In terms of power at a constant bandwidth, red
        % noise falls off at 6 dB/oct, i.e. 20 dB/dec.
        % define the length of the noise vector and ensure
        % that M is even, this will simplify the processing
        m = round(m); n = round(n); N = m*n;
        if rem(N, 2)
            M = N+1;
        else
            M = N;
        end
        % generate white noise sequence
        x = randn(1, M);
        % FFT
        X = fft(x);
        % prepare a vector with frequency indexes
        NumUniquePts = M/2 + 1;     % number of the unique fft points
        k = 1:NumUniquePts;         % vector with frequency indexes
        % manipulate the left half of the spectrum so the PSD
        % is proportional to the frequency by a factor of 1/(f^2),
        % i.e. the amplitudes are proportional to 1/f
        X = X(1:NumUniquePts);
        X = X./k;
        % prepare the right half of the spectrum - a conjugate copy of the left
        % one except the DC component and the Nyquist component - they are unique,
        % and reconstruct the whole spectrum
        X = [X conj(X(end-1:-1:2))];
        % IFFT
        y = real(ifft(X));
        % ensure that the length of y is N
        y = y(1, 1:N);
        % form the noise matrix and ensure unity standard
        % deviation and zero mean value (columnwise)
        y = reshape(y, [m, n]);
        y = bsxfun(@minus, y, mean(y));
        y = bsxfun(@rdivide, y, std(y));
    end



    function y = violetnoise(m, n)
        % function: y = violetnoise(m, n)
        % m - number of matrix rows
        % n - number of matrix columns
        % y - matrix with violet noise samples
        %     with mu = 0 and sigma = 1 (columnwise)
        % The function generates a matrix of violet noise samples
        % (columnwise). In terms of power at a constant bandwidth,
        % violet noise increase in at 6 dB/oct, i.e. 20 dB/dec.
        % difine the length of the noise vector and ensure
        % that M is even, this will simplify the processing
        m = round(m); n = round(n); N = m*n;
        if rem(N, 2)
            M = N+1;
        else
            M = N;
        end
        % generate white noise sequence
        x = randn(1, M)*0.1;
        % FFT
        X = fft(x);
        % prepare a vector with frequency indexes
        NumUniquePts = M/2 + 1;     % number of the unique fft points
        k = 1:NumUniquePts;         % vector with frequency indexes
        % manipulate the left half of the spectrum so the PSD
        % is proportional to the frequency by a factor of f^2,
        % i.e. the amplitudes are proportional to f
        X = X(1:NumUniquePts);
        X = X.*k;
        % prepare the right half of the spectrum - a conjugate copy of the left
        % one except the DC component and the Nyquist component - they are unique,
        % and reconstruct the whole spectrum
        X = [X conj(X(end-1:-1:2))];
        % IFFT
        y = real(ifft(X));
        % ensure that the length of y is N
        y = y(1, 1:N);
        % form the noise matrix and ensure unity standard
        % deviation and zero mean value (columnwise)
        y = reshape(y, [m, n]);
        y = bsxfun(@minus, y, mean(y));
        y = bsxfun(@rdivide, y, std(y));
    end


    function y = bluenoise(m, n)
        % function: y = bluenoise(m, n)
        % m - number of matrix rows
        % n - number of matrix columns
        % y - matrix with blue noise samples
        %     with mu = 0 and sigma = 1 (columnwise)
        % The function generates a matrix of blue noise samples
        % (columnwise). In terms of power at a constant bandwidth,
        % blue noise increase in at 3 dB/oct, i.e. 10 dB/dec.
        % difine the length of the noise vector and ensure
        % that M is even, this will simplify the processing
        m = round(m); n = round(n); N = m*n;
        if rem(N, 2)
            M = N+1;
        else
            M = N;
        end
        % generate white noise sequence
        x = randn(1, M)*0.1;
        % FFT
        X = fft(x);
        % prepare a vector with frequency indexes
        NumUniquePts = M/2 + 1;     % number of the unique fft points
        k = 1:NumUniquePts;         % vector with frequency indexes
        % manipulate the left half of the spectrum so the PSD
        % is proportional to the frequency by a factor of f,
        % i.e. the amplitudes are proportional to sqrt(f)
        X = X(1:NumUniquePts);
        X = X.*sqrt(k);
        % prepare the right half of the spectrum - a conjugate copy of the left
        % one except the DC component and the Nyquist component - they are unique,
        % and reconstruct the whole spectrum
        X = [X conj(X(end-1:-1:2))];
        % IFFT
        y = real(ifft(X));
        % ensure that the length of y is N
        y = y(1, 1:N);
        % form the noise matrix and ensure unity standard
        % deviation and zero mean value (columnwise)
        y = reshape(y, [m, n]);
        y = bsxfun(@minus, y, mean(y));
        y = bsxfun(@rdivide, y, std(y));
    end
end
