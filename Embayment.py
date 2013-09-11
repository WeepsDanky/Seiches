'''
Created on Jun 11, 2012

@author: bogdan
'''
import fft.FFTGraphs as FFTGraphs
import fft.fft_utils as fft_utils
import fft.Filter as Filter
import wavelets.Graphs
import wavelets.kCwt
import scipy as sp
import numpy as np
import math
import matplotlib.mlab as mlab
import EmbaymentPlot
from optparse import OptionParser

path = '/software/software/scientific/Matlab_files/Helmoltz/Embayments-Exact/LakeOntario-data'
path1 = '/software/software/scientific/Matlab_files/Helmoltz/Embayments-Exact/Data-long/FMB'
path2 = '/software/software/scientific/Matlab_files/Helmoltz/Embayments-Exact/Data-long/LOntario'
path3 = '/software/software/scientific/Matlab_files/Helmoltz/Embayments-Exact/Toronto_Harbour'
path4 = '/home/bogdan/Documents/UofT/PhD/Data_Files/Toberymory_tides'

embayments = {'FMB' : {'A':850000., 'B':25. , 'H':1., 'L':130.,
                       'Period':[12.2, 5.065, 1.38, 0.81, 0.48] ,  # h
                       'Amplitude':[0.0365, 0.023, 0.015, 0.018, 0.016],  # m
                       'Amplitude_bay':[0.0365, 0.023, 0.015, 0.018, 0.016],  # m
                       'Phase':[5, 22, -15, 39, -4.6],  # rad
                       'CD':0.0032,
                       'filename':path + '/Inner_Harbour_July_processed.csv'},
              'Tob-IBP-ex' : {'A':150000., 'B':140. , 'H':2.143, 'L':570.,
                       'Period':[16.8 / 60, 12.0 / 60, 8.0 / 60, 5.35 / 60, 4.5 / 60] ,  # h
                       'Amplitude':[0.02, 0.018, 0.016, 0.015, 0.018],  # m
                       'Phase':[0, 0, 0, 0, 0],  # rad
                       'CD':0.0032,
                       'filename':path4 + '/LL1.csv'},
              'Tob-IBP' : {'A':145000., 'B':140. , 'H':2.143, 'L':570.,
                       'Period':[16.8 / 60, 12.0 / 60, 8.0 / 60] ,  # h
                       'Amplitude':[0.02, 0.018, 0.016],  # m
                       'Amplitude_bay':[0.09, 0.043, 0.058],  # m
                       'Phase':[0, 0, 0],  # rad
                       'CD':0.0032,
                       'filename':path4 + '/LL1.csv'},
              'Tob-CIH' : {'A':64000., 'B':56. , 'H':1.9, 'L':175.,
                       'Period':[16.8 / 60, 12.0 / 60, 9.2 / 60] ,  # h
                       'Amplitude':[0.02, 0.018, 0.014],  # m
                       'Amplitude_bay':[0.025, 0.078, 0.037],  # m
                       'Phase':[0, 0, 0],  # rad
                       'CD':0.0032,
                       'filename':path4 + '/LL4.csv'},
              'L-SUP' : {'A':180000., 'B':30. , 'H':1., 'L':2000.,
                       'Period':[2.9, 2.9] ,  # h
                       'Amplitude':[0.1, 0.1],  # m
                       'Phase':[0, 0],  # rad
                       'CD':0.0032,
                       'filename':None},

              }







class Embayment(object):
    '''
    classdocs
    '''

    def __init__(self, name):
        '''
        Constructor
        '''
        # name can be: 'FMB', 'Emb_A', 'Tob-CIH', 'Tob-IBP'
        self.name = name
        dict = embayments[name]
        self.A = dict['A']
        self.B = dict['B']
        self.H = dict['H']
        self.L = dict['L']
        self.Period = dict['Period']
        self.Amplitude = dict['Amplitude']
        self.Phase = dict['Phase']
        self.Cd = dict['CD']
        self.filename = dict['filename']

    @staticmethod
    def plotMultipleTimeseries(path_in, filenames, names, detrend = False, filtered = False, lowcut = None, highcut = None, tunits = 'sec'):
        # plot the original Lake oscillation input
        ts = []
        i = 0
        time = []
        for filename in filenames:
            [Time, SensorDepth] = fft_utils.readFile(path_in, filename)
            # must detrend from subtracting the median so all have a zero median
            if filtered:
                # filtered timeseries
                N = 5
                if tunits == 'day':
                    factor = 86400
                elif tunits == 'hour':
                    factor = 3600
                else:
                    factor = 1
                dt_s = (Time[2] - Time[1]) * factor  # Sampling period [s]
                samp_rate = 1.0 / dt_s
                btype = 'band'
                # y = fft_utils.filters.fft_bandpassfilter(SensorDepth, samp_rate, lowcut, highcut)
                y, w, h, N, delay = fft_utils.filters.butterworth(SensorDepth, btype, lowcut, highcut, samp_rate, order = 5)
                SensorDepth = y
            # end if filtered

            ts.append(sp.signal.detrend(SensorDepth))
            time.append(Time)
            i += 1
        series = np.array(ts)


        L = len(Time)
        xlabel = 'Time [days]'
        ylabel = 'Detrended Z(t) [m]'
        xa = np.array(time)

        # This is a moving average detrend
        if detrend:
            series2 = []
            # time2 = []
            for i in range(0, len(series)):
                x = fft_utils.detrend(series[i])
                # x = fft_utils.smoothSeriesWindow(series[i], 100)
                series2.append(x)
            series = np.array(series2)
            # xa = np.array(time2)


        legend = names
        # end
        fft_utils.plot_n_TimeSeries("Detrended Lake and Bay Levels", xlabel, ylabel, xa, series, legend)



    # end plotLakeLevels

    @staticmethod
    def SpectralAnalysis(b_wavelets = False, window = "hanning", num_segments = None, tunits = 'day', funits = "Hz", filter = None, log = False):

        # show extended calculation of spectrum analysis
        show = True
        bay = bayname
        bay_names = []
        lake_name = ""
        bay_name = ""
        tunits = "day"
        if bay == 'FMB':
            # Frenchman's bay data
            fftsa = FFTGraphs.FFTGraphs(path, 'Lake_Ontario_1115682_processed.csv', 'Inner_Harbour_July_processed.csv', show, tunits)
            lake_name = "Lake Ontario"
            bay_name = "Frenchman's bay"
        elif bay == 'BUR':
            # Burlington data    43.333333N , 79.766667W (placed in the lake not the sheltered bay)
            fftsa = FFTGraphs.FFTGraphs(path, 'LO_Burlington-JAN-DEC-2011_date.csv', None, show, tunits)
            # fftsa = FFTGraphs.FFTGraphs(path, 'LO_Burlington-Apr26-Apr28-2011.csv', None, show, tunits)
            lake_name = "Lake  Ontario"
            bay_name = ""
        # Fathom Five National Park Outer Boat Passage
        elif bay == 'Tob-OBP':
            # NOTE:lake amplit is lower so switch places
            fftsa = FFTGraphs.FFTGraphs(path4, 'LL3.csv', 'LL2.csv', show, tunits)
            # fftsa = FFTGraphs.FFTGraphs(path4, 'LL3-28jul2010.csv', 'LL2-28jul2010.csv', show , tunits)
            lake_name = "Harbour Island - lake"  # LL3.csv is actually the lake
            bay_name = "Outer Boat Passage"
        # Fathom Five National Park Inner Boat Passage
        elif bay == 'Tob-IBP':
            # NOTE:lake amplit is lower so switch places
            # fftsa = FFTGraphs.FFTGraphs(path4, 'LL3.csv', 'LL1.csv', show, tunits)
            fftsa = FFTGraphs.FFTGraphs(path4, 'LL3-28jul2010.csv', 'LL1-28jul2010.csv', show, tunits)

            lake_name = "Harbour Island - lake"  # LL3.csv is actually the lake
            bay_name = "Inner Boat Passage"
        # Fathom Five National Park Cove Island Harbour
        elif bay == 'Tob-CIH':
            # NOTE:lake amplit is lower so switch places
            # fftsa = FFTGraphs.FFTGraphs(path4, 'LL3.csv', 'LL4.csv', show, tunits)
            fftsa = FFTGraphs.FFTGraphs(path4, 'LL3-28jul2010.csv', 'LL4-28jul2010.csv', show, tunits)
            lake_name = "Harbour Island - lake"  # LL3.csv is actually the lake
            bay_name = "Cove Island Harbour"  #
        elif bay == 'Tob-HI':
            # NOTE:lake amplit is lower so switch places
            # fftsa = FFTGraphs.FFTGraphs(path4, 'LL3.csv', 'LL3.csv', show, tunits)
            fftsa = FFTGraphs.FFTGraphs(path4, 'LL3-28jul2010.csv', 'LL3-28jul2010.csv', show, tunits)
            lake_name = "Harbour Island - lake"  # LL3.csv is actually the lake
            bay_name = "Harbour Island - lake"  #
        # Embayment A Tommy Thomson Park
        elif bay == 'Emb-A':
            fftsa = FFTGraphs.FFTGraphs(path3, '1115865-Station16-Gate-date.csv', '1115861-Station14-EmbaymentA-date.csv', show, tunits)
            lake_name = "Lake Ontario"
            bay_name = " Emabayment A"

        elif bay == 'Tob_All':
            fftsa1 = FFTGraphs.FFTGraphs(path4, 'LL4-28jul2010.csv', None, show, tunits)
            bay_names.append("Cove Island Harbour")
            fftsa2 = FFTGraphs.FFTGraphs(path4, 'LL1-28jul2010.csv', None, show, tunits)
            bay_names.append("Inner Boat Passage")
            fftsa3 = FFTGraphs.FFTGraphs(path4, 'LL2-28jul2010.csv', None, show , tunits)
            bay_names.append("Outer Boat Passage")
            fftsa4 = FFTGraphs.FFTGraphs(path4, 'LL3-28jul2010.csv', None, show , tunits)
            bay_names.append("Harbour Island - lake")
        else:
            print "Unknown embayment"
            exit(1)
        # end

        if bay == 'Tob_All':
            showLevels = False
            detrend = False
            draw = False
            fftsa1.doSpectralAnalysis(showLevels, draw, tunits, window, num_segments, filter, log)
            fftsa2.doSpectralAnalysis(showLevels, draw, tunits, window, num_segments, filter, log)
            fftsa3.doSpectralAnalysis(showLevels, draw, tunits, window, num_segments, filter, log)
            fftsa4.doSpectralAnalysis(showLevels, draw, tunits, window, num_segments, filter, log)

            data = [fftsa1.mx, fftsa2.mx, fftsa3.mx, fftsa4.mx]
            ci05 = [fftsa1.x05, fftsa2.x05, fftsa3.x05, fftsa4.x05]
            ci95 = [fftsa1.x95, fftsa2.x95, fftsa3.x95, fftsa4.x95]
            freq = [fftsa1.f, fftsa2.f, fftsa3.f, fftsa4.f]
            FFTGraphs.plotSingleSideAplitudeSpectrumFreqMultiple(lake_name, bay_names, data, freq, [ci05, ci95], num_segments, funits, y_label = None, title = None, log = log, fontsize = 20, tunits = tunits)

        else:
            showLevels = False
            detrend = False
            draw = False
            fftsa.doSpectralAnalysis(showLevels, draw, tunits, window, num_segments, filter, log)
            fftsa.plotLakeLevels(lake_name, bay_name, detrend)
            fftsa.plotSingleSideAplitudeSpectrumFreq(lake_name, bay_name, funits, y_label = None, title = None, log = log, fontsize = 20, tunits = tunits)
            fftsa.plotPowerDensitySpectrumFreq(lake_name, bay_name, funits)  # = "Hz", y_label = None, title = None, log = False, fontsize = 20, tunits = None):
            fftsa.plotSingleSideAplitudeSpectrumTime(lake_name, bay_name)

            # fftsa.plotZoomedSingleSideAplitudeSpectrumFreq()
            # fftsa.plotZoomedSingleSideAplitudeSpectrumTime()
            # fftsa.plotCospectralDensity()
            fftsa.plotPhase()

            if b_wavelets:
                # Wavelet Spectral analysis
                if bay == 'FMB':
                    graph = wavelets.Graphs.Graphs(path, 'Lake_Ontario_1115682_processed.csv', 'Inner_Harbour_July_processed.csv', show)
                elif bay == 'BUR':
                    graph = wavelets.Graphs.Graphs(path, 'LO_Burlington-JAN-DEC-2011_date.csv', None, show)
                    # graph = wavelets.Graphs.Graphs(path, 'LO_Burlington-Apr26-Apr28-2011.csv', None, show)
                elif bay == 'Tob-OBP':
                    graph = wavelets.Graphs.Graphs(path4, 'LL3.csv', 'LL2.csv', show)
                    # graph = wavelets.Graphs.Graphs(path4, 'LL3-28jul2010.csv', 'LL2-28jul2010.csv', show)
                elif bay == 'Tob-IBP':
                    graph = wavelets.Graphs.Graphs(path4, 'LL3.csv', 'LL1.csv', show)
                    # graph = wavelets.Graphs.Graphs(path4, 'LL3-28jul2010.csv', 'LL1-28jul2010.csv', show)
                # Fathom Five National Park Cove Island Harbour
                elif bay == 'Tob-CIH':
                    graph = wavelets.Graphs.Graphs(path4, 'LL3.csv', 'LL4.csv', show)
                    # graph = wavelets.Graphs.Graphs(path4, 'LL3-28jul2010.csv', 'LL4-28jul2010.csv', show)
                elif bay == 'Tob-HI':
                    graph = wavelets.Graphs.Graphs(path4, 'LL3.csv', 'LL3.csv', show)
                    # graph = wavelets.Graphs.Graphs(path4, 'LL3-28jul2010.csv', 'LL3-28jul2010.csv', show)
                # Embayment A Tommy Thomson Park
                elif bay == 'Emb-A':
                    graph = wavelets.Graphs.Graphs(path3, '1115865-Station16-Gate-date.csv', '1115861-Station14-EmbaymentA-date.csv', show)
                else:
                    print "Unknown embayment"
                    exit(1)

                graph.doSpectralAnalysis()
                graph.plotDateScalogram(scaleType = 'log', plotFreq = True)
                graph.plotSingleSideAplitudeSpectrumTime()
                graph.plotSingleSideAplitudeSpectrumFreq()
                graph.showGraph()
            # nd if b_wavelets
    # end SpectralAnalysis

    @staticmethod
    def HarmonicAnalysis(filename, freq_hours):

        [Time, SensorDepth] = fft_utils.readFile(path, filename)
        y = sp.signal.detrend(SensorDepth)
        miu = np.mean(y)
        T = freq_hours * 3600
        om = 2 * np.pi / T
        tunits = "day"
        if tunits == 'day':
            factor = 86400
        elif tunits == 'hour':
            factor = 3600
        else:
            factor = 1

        dt_s = (Time[2] - Time[1]) * factor  # Sampling period [s]
        A = 0.0
        B = 0.0
        for i in range(0, len(y)) :
            t = i * dt_s
            A += (y[i] - miu) * math.cos(om * t)
            B += (y[i] - miu) * math.sin(om * t)
        A = 2.0 / len(y) * A
        B = 2.0 / len(y) * B
        R = np.sqrt(A ** 2 + B ** 2)
        print ("amplitude (m): %f") % R
    # end HarmonicAnalysis

    @staticmethod
    def waveletAnalysis(title, tunits, slevel, avg1, avg2, val1, val2, \
                        dj = None, s0 = None, J = None, alpha = None):

        ppath = path
        if self.name == 'FMB':
            # Frenchman's bay data
            ppath = path
            file = 'Lake_Ontario_1115682_processed.csv'
        elif self.name == 'BUR':
            # Burlington data    43.333333N , 79.766667W (placed in the lake not ht sheltered bay)
            ppath = path
            file = 'LO_Burlington-Apr26-Apr28-2011.csv'
        # Fathom Five National Park Outer Boat Passage
        elif self.name == 'Tob-OBP':
            ppath = path4
            file = 'LL2.csv'
            # file = 'LL1-28jul2010.csv'
        elif bay == 'Tob-IBP':
            ppath = path4
            file = 'LL1.csv'
        # Fathom Five National Park Cove Island Harbour
        elif self.name == 'Tob-CIH':
            ppath = path4
            file = 'LL4.csv'
            # file = 'LL4-28jul2010.csv'
        # Embayment A Tommy Thomson Park
        elif self.name == 'Emb-A':
            ppath = path3
            file = '1115865-Station16-Gate-date.csv'
        else:
            print "Unknown embayment"
            exit(1)
        kwavelet = wavelets.kCwt.kCwt(ppath, file, tunits)
        dj = 0.05  # Four sub-octaves per octaves
        s0 = -1  # 2 * dt                      # Starting scale, here 6 months
        J = -1  # 7 / dj                      # Seven powers of two with dj sub-octaves
        alpha = 0.5  # Lag-1 autocorrelation for white noise

        kwavelet.doSpectralAnalysis(title, "morlet", slevel, avg1, avg2, dj, s0, J, alpha)
        ylabel_ts = "amplitude"
        yunits_ts = 'm'
        xlabel_sc = ""
        ylabel_sc = 'Period (%s)' % kwavelet.tunits
        # ylabel_sc = 'Freq (Hz)'
        sc_type = "period"
        # sc_type = "freq"
        x_type = 'date'
        kwavelet.plotSpectrogram(ylabel_ts, yunits_ts, xlabel_sc, ylabel_sc, sc_type, x_type, val1, val2)
        ylabel_sc = 'Frequency ($s^{-1}$)'
        kwavelet.plotAmplitudeSpectrogram(ylabel_ts, yunits_ts, xlabel_sc, ylabel_sc, sc_type, x_type, val1, val2)

    def EmbaymentFlow(self, A, HbVect, dt):
        '''
        calculates flow in the channel based on water level fluctuations in the
        embayment
        '''
        Q = np.zeros(len(HbVect))
        for i in range(1, len(HbVect)):
            Q[i] = A * (HbVect[i - 1] - HbVect[i]) / dt
        # end
        return Q
    # end EmbaymentFlow

    def CalculateFlow(self, days):
        # Water exchange
        #
        #
        # Calculate the Flow in the Embayment
        #
        Cd_const = False

        filename1 = 'Inner_Harbour_July_processed.csv'
        # [Time1,SensorDepth1] = textread(filename1, '%f %f' ,-1,'delimiter', ',');
        # resample to be the same as first
        '''
        ts=timeseries(SensorDepth1,Time1,'Name','level');
        ts=transpose(ts);
        res_ts=resample(ts,Time);
        SensorDepth2=res_ts.data(:); %get(res_ts,'Data');
        % predicted
        '''
        embPlot = EmbaymentPlot.EmbaymentPlot(self)
        [t, X, c, k, w, x0, v0, R] = embPlot.Response(days)
        embPlot.plotForcingResponse(t)
        embPlot.plotRespVsOmegaVarAmplit()
        embPlot.plotRespVsOmegaVarFric()
        embPlot.plotPhaseVsOmega()
        embPlot.plotRespVsOmegaVarArea()
        embPlot.plotRespVsOmegaVarMouth()
        embPlot.plotRespVsOmegaVarMouthCurves()
        embPlot.plotDimensionlessResponse()
        embPlot.show()

        Qp = self.EmbaymentFlow(self.A, R, (t[2] - t[1]) * 86400)

        Vp = 0
        sumpred = 0
        for i in range(0, len(Qp) - 1):
            sumpred = sumpred + 0.5 * np.abs(R[i] - R[i - 1])
            if ((Qp[i] - Qp[i - 1]) > 0) and (Qp[i] > 0) :
                Vp = Vp + (Qp[i] + Qp[i - 1]) / 2 * 300;
            # end
        # end

        print "V pred=%f, Sum pred=%f" % (Vp, sumpred)

        [Time, SensorDepth] = fft_utils.readFile("", self.filename)
        Qm = self.EmbaymentFlow(self.A, SensorDepth, (Time[2] - Time[1]) * 86400)

        Vm = 0
        summeas = 0
        for i in range(0, len(Qm) - 1):
            summeas = summeas + 0.5 * np.abs(SensorDepth[i] - SensorDepth[i - 1])
            if ((Qm[i] - Qm[i - 1]) > 0) and (Qm[i] > 0) :
                Vm = Vm + (Qm[i] + Qm[i - 1]) / 2 * 300;
            # end
        # end

        print "V meas=%f Sum meas=%f" % (Vm, summeas)


        '''
        y=detrend(SensorDepth2);
        %use smoothed time-series to eliminate oscillations, which do not
        %contribute to flushing.
        y2=smoothSeries(SensorDepth2,8); %30 minutes
        % measured
        Q2=self.EmbaymentFlow(self.A,self.B,self.H,SensorDepth2,(Time(2)-Time(1))*86400);
        figure;
        [titl, errmsg] = sprintf('FM Bay Flow vs.  Time Diagram\n Cd=%4.3f[m] H=%4.1f B=%4.1f[m] L=%4.1f[m]',Cd,H,B,L);
        %plot(t(10:length(Q)),Q(10:length(Q)),'b'),xlabel('time [s]'), ylabel('Q [m^3/s]'), title(titl), grid on, hold  on
        tt=Time'; % transpose
        plot(tt(1:length(Q)),Q,'b'),xlabel('time [s]'), ylabel('Q [m^3/s]'), title(titl), grid on, hold  on

        plot(tt(1:length(Q)),Q2(1:length(Q)),'-.r');
        h = legend('predicted','measured',2, 'location', 'NorthEast');

        %plot the original Lake oscillation input
        L = length(Q);
        xlim = [tt(1),tt(L)];  % plotting range
        Xticks = tt(1):(tt(length(Q))-tt(1))/3:tt(length(Q));
        Xtickslabel={};
        for i in range(0, len(Xticks)):
            Xtickslabel{i}=datestr(Xticks(i),' mmm dd HH:MM')
        #end for
        set(gca,'XLim',xlim(:),    'XTick',Xticks(:),'XTickLabel',Xtickslabel(:));


        summeas=0
        sumpred=0
        Vp=0;
        for i in range(1,len(Q)):
            sumpred=sumpred+0.5*abs(R(i)-R(i-1));
            if ((Q(i) - Q(i-1)) >0) && (Q(i) > 0 ): #&& (Q(i-1) >0)
                Vp=Vp+(Q(i)+Q(i-1))/2*300
            #end if
        #end for

        Vm=0;
        for i=2:length(Q)
            %{
            if (SensorDepth2(i)-SensorDepth2(i-1) > 0) && (SensorDepth2(i) >0)
                summeas=summeas+0.5*(SensorDepth2(i)-SensorDepth2(i-1));
            end
            %}
            %summeas=summeas+0.5*abs(SensorDepth2(i)-SensorDepth2(i-1));
            summeas=summeas+0.5*abs(y2(i)-y2(i-1));
            if ((Q2(i) - Q2(i-1)) >0) && (Q2(i) > 0 ) %&& (Q2(i-1) >0)
                Vm=Vm+(Q2(i)+Q2(i-1))/2*300;
            end
        end



        print 'Sum measured %f' % summeas
        print 'Sum predicted %f' % sumpred
        print 'Vol meas %f' % Vm
        print 'Vol pred %f ', Vp
        '''
    # end CalculateFlow

    @staticmethod
    def CalculateSpectral(bay):
        showLevels = False
        detrend = False
        # detrend = True

        filenames = ['LL1.csv', 'LL4.csv', 'LL2.csv', 'LL3.csv']
        # filenames = ['LL3.csv', '11690-01-JUL-2010_out.csv']
        # filenames = ['LL1-28jul2010.csv', 'LL4-28jul2010.csv', 'LL2-28jul2010.csv', 'LL3-28jul2010.csv']

        names = [ "Inner Boat Passage" , "Cove Island Harbour", "Outer Boat Passage", "Harbour Island - lake"]
        # names = ["Harbour Island - lake", "Station 11960"]

        # set to True for Butterworth filtering - just for testing.
        doFiltering = False
        lowcutoff = 1.157407e-5
        highcutoff = 0.00834
        tunits = 'day'  # can be 'sec', 'hour'
        funits = "cph"
        Embayment.plotMultipleTimeseries(path4, filenames, names, detrend, doFiltering , lowcutoff, highcutoff, tunits)


        doSpectral = True
        dowavelets = True
        doWavelet = True
        doHarmonic = False
        doFiltering = False
        tunits = 'day'  # can be 'sec', 'hour'
        window = 'hanning'
        num_segments = 10

        btype = 'band'
        if btype == 'low':  # pass freq < lowcutoff
            highcutoff = None
            lowcutoff = 0.00834 * 2  # Hz => 30 cph, or T=2 min
        elif btype == 'high':  # pass freq > highcutoff
            highcutoff = 1.157407e-5  # Hz => 0.0417 cph, or T=24 h
            lowcutoff = None
        elif btype == 'band':  # pass highcutoff > freq > lowcutoff
            lowcutoff = 1.157407e-5  # Hz => 0.0417 cph, or T=24 h
            highcutoff = 0.00834  # Hz => 30 cph, or T=2 min


        ftype = 'fft'
        # ftype = 'butter' THIS DOES NOT WORK PROPERLY for the random signal we have here
        if doFiltering:
            filter = [lowcutoff, highcutoff]  # Filter.Filter(doFiltering, lowcutoff, highcutoff, btype)
        else:
            filter = None

        log = False
        if doSpectral:
            Embayment.SpectralAnalysis(dowavelets, window, num_segments, tunits, funits, filter, log)

        tunits = 'day'
        slevel = 0.95
        # range 0-65000 is good to catch the high frequencies
        #       0-600000 if you need to catch internal waves with much lower frequencies and large periods
        val1, val2 = (0, 65000)  # Range of sc_type (ex periods) to plot in spectogram
        avg1, avg2 = (0, 65000)  # Range of sc_type (ex periods) to plot in spectogram

        title = bay + ""
        if doWavelet :
            Embayment.waveletAnalysis(title, tunits, slevel, avg1, avg2, val1, val2)

        if doHarmonic:
            freq_hours = 4.5
            Embayment.HarmonicAnalysis('Lake_Ontario_1115682_processed.csv', freq_hours)
            Embayment.HarmonicAnalysis('LO_Burlington-Mar23-Apr23-2011.csv', freq_hours)
            Embayment.HarmonicAnalysis('LO_Burlington-JAN-DEC-2011_date.csv', freq_hours)
            Embayment.HarmonicAnalysis('LO_Burlington-Apr26-Apr28-2011.csv', freq_hours)
    # end CalculateSpectral

# end Embayment


if __name__ == '__main__':
    bay = 'Emb-A'
    bay = 'FMB'
    # bay = 'BUR'
    # bay = 'Tob-OBP'
    bay = 'Tob-IBP'
    bay = 'Tob-CIH'
    # bay = 'Tob_All'
    # bay = 'Tob-HI'
    # bay = 'L-SUP'
    days = 0.2

    usage = "usage: %prog [options] arg"
    parser = OptionParser(usage)
    parser.add_option("-s", "--spectral", dest = "sp", action = "store_true", default = False, help = "Spectral analysis")
    parser.add_option("-f", "--flushing", dest = "fl", action = "store_true", default = False, help = "Flusing timescales")
    (options, args) = parser.parse_args()
    if options.sp:
        print "* Calculate Spectral *"
        Embayment.CalculateSpectral(bay)
    else:
        print ">> NOT Calculate Spectral <<"
    if options.fl:
        print "* Calculate Flow *"
        emb = Embayment(bay)
        emb.CalculateFlow(days)

    else:
        print ">> NOT Calculate Flow <<"
    print "Done."
