import sys
print sys.path
import tools.trebitz_graphs as tg
import numpy as np
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, FormatStrFormatter
from scipy.interpolate import interp1d
import utools.stats as ustats

#############
# constants
#############
# gravity [m/s^2]
g = 9.81

# head loss due to flow separation
f = 1.55

# special characters
omega_char = unichr(0x3c9).encode('utf-8')
alfa_char = unichr(0x3b1).encode('utf-8')
alpha0 = r'$\alpha_0$'
omega0 = r'$\omega_0$'
alphae = r'$\alpha_e$'
alpha = r'$\alpha$'
omega = r'$\omega$'

class EmbaymentPlot(object):

    def __init__(self, bay):
        self.location_name = bay.name
        self.A = bay.A
        self.B = bay.B
        self.H = bay.H
        self.L = bay.L
        self.Period = bay.Period
        self.Amplitude = bay.Amplitude
        self.Phase = bay.Phase
        self.Cd = bay.Cd
        self.w0 = None


        # local arrays
        self.w = np.zeros(len(self.Amplitude), dtype = np.ndarray)  # angular frequency
        self.X = np.zeros(len(self.Amplitude), dtype = np.ndarray)  # Bay oscillations
        self.fwave = np.zeros(len(self.Amplitude), dtype = np.ndarray)  # forcing oscillations (lake)
        self.c = np.zeros(len(self.Amplitude), dtype = np.ndarray)  # damping effect
        self.k = np.zeros(len(self.Amplitude), dtype = np.ndarray)  # elastic constant
        self.Fa = np.zeros(len(self.Amplitude), dtype = np.ndarray)  # equivalent elastic force
        self.phy = np.zeros(len(self.Amplitude), dtype = np.ndarray)  # phase
        self.tsup = np.zeros(len(self.Amplitude), dtype = np.ndarray)  # supplementary period due to phase lag
        self.G = np.zeros(len(self.Amplitude), dtype = np.ndarray)  # hypothetic response of an oscillator

    def show(self):
        plt.show()

    def amplitudef(self, amplitude_e, w, w0, n0):
        '''
        This is eq (3) from Terra et al. (2005), the bay (resulting) amplitude
        '''
        ampl = np.absolute(amplitude_e) * \
                np.sqrt((np.sqrt((1 - (w / w0) ** 2) ** 4 + 4 * n0 ** 2 * (w / w0) ** 4 * (np.absolute(amplitude_e)) ** 2) - \
                      (1 - (w / w0) ** 2) ** 2) / (2 * n0 ** 2 * (w / w0) ** 4 * (np.absolute(amplitude_e)) ** 2))
        return ampl
        # end amplitudef

    def calculateResponseVsAngularFreqSlow(self, a0, om, False):
        O = self.B * self.H
        # head loss coeff. includes flow separation and bottom friction
        fm = self.L * (f / self.L + self.Cd / self.H)

        # linearized loss term coefficient
        n0 = 8 * fm * self.A / (3 * np.pi * O * self.L)

        # eigenfrequency
        w0 = np.sqrt(g * O / self.L / self.A);


        A = np.zeros(len(om))
        i = 0
        for w in om:
            A[i] = self.amplitudef(a0, w, w0, n0)
            i += 1

        return A

    def max_amplification (self, amplitude_e, n0):
        '''
        This is eq (4) from Terra et al. (2005), the bay (resulting) max amplitude
        '''
        ampl_max = np.absolute(amplitude_e) * np.sqrt(0.5 + 0.5 * np.sqrt(1 + 4. / (n0 ** 2 * np.absolute(amplitude_e)) ** 2))
        return ampl_max



    def dl_amplitudef(self, dlamplitude_e, dlw):
        dln0 = 8 / (3 * np.pi);
        ampl = np.sqrt((np.sqrt((1 - (dlw) ** 2) ** 4 + 4 * dln0 ** 2 * (dlw) ** 4 * (np.abs(dlamplitude_e)) ** 2) - \
                     (1 - (dlw) ** 2) ** 2) / (2 * dln0 ** 2 * (dlw) ** 4))

        return ampl
    # end


    def fourierODE(self, m, c, k, Fa, w):
        '''
        % [x,v]=solveODE(m,c,k,f,w,x0,v0,t)
        % ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        % This function solves the differential equation
        % a*x''(t)+b*x'(t)+c*x(t)=f(t)
        % with x(0)=x0 and x'(0)=v0
        %
        % m,c,k  - mass, damping and stiffness coefficients
        % f1     - the forcing function
        % w      - frequency of the forcing function
        % t      - vector of times to evaluate the solution
        % x,v    - computed position and velocity vectors
        % wn     - w0 eigenfrequency
        '''
        F = np.zeros(len(w))

        ccrit = 2 * np.sqrt(m * k)
        wn = np.sqrt(k / m)  # or w0 - natural frequency of the system

        # If the system is undamped and resonance will
        # occur, add a little damping
        if c == 0 :  # and w == wn:
            c = ccrit / 1e6
        # end if

        # If damping is critical, modify the damping
        # very slightly to avoid repeated roots
        if c == ccrit:
            c = c * (1 + 1e-6)
        # end if

        # Forced response particular solution
        for i in range(0, len(w)):
            # F[i] = np.abs(Fa / (k - m * w[i] ** 2 + 1j * c * w[i]))  # - OLD matlab Still good
            F[i] = Fa / np.sqrt((k - m * w[i] ** 2) ** 2 + (c * w[i]) ** 2)
        # end for

        return F
    # fourierODE

    def phaseODE(self, n0, w0, amplitude_e, om):

        amplitude = np.zeros(len(om))
        PHI = np.zeros(len(om))

        for j in range(0, len(om)):
            amplitude[j] = abs(amplitude_e) * np.sqrt((np.sqrt((1 - (om[j] / w0) ** 2) ** 4 + 4 * n0 ** 2 * (om[j] / w0) ** 4 * (abs(amplitude_e)) ** 2)\
                 - (1 - (om[j] / w0) ** 2) ** 2) / (2 * n0 ** 2 * (om[j] / w0) ** 4 * (abs(amplitude_e)) ** 2))

            PHI[j] = np.arccos((1 - (om[j] / w0) ** 2) * amplitude[j] / amplitude_e)
        # end for
        return PHI


    def  Response(self, days):
            '''
            % ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            % This function plots the response and animates the
            % motion of a damped linear harmonic embayment oscillator
            % characterized by the differential equation
            % z''+n0*w*|alpha|*z'-w0^2*z=w0^2*ze(t)
            % with initial conditions x(0)=x0, x'(0)=v0.
            % The animation depicts forced motion of a block
            % attached to a wall by a spring. The block
            % slides on a horizontal plane which provides
            % viscous damping.

            % example - Omit this parameter for interactive input.
            %           Use smdplot(1) to run a sample problem.
            % t,X     - time vector and displacement response
            % m,c,k   - mass, damping coefficient,  replaced with a,b,c
            %           spring stiffness constant
            % w0      - eigen frequency
            % A       - area of the embayment
            % L       - length of the channel
            % B       - channel width
            % H       - channel depth
            % fm      - head loss coefficient ( fm/L )
            % O       - B*H  - channel cross section
            % n0      - 8*fm*A/(3*pi*O*L)
            % g       - gravitational acceleration 9.81 m/s^2
            %
            % f1,f2,w - force components and forcing frequency
            % x0,v0   - initial position and velocity
            %
            % User m functions called: spring smdsolve inputv
            % -----------------------------------------------
            '''
            #===============================================================================
            print ('SOLUTION FOR z\"+n*w*a*z\'-w0^2*z=w0^2*ze')
            print('Width: %f') % self.B

            tmax = days * 86400;
            nt = days * 24 * 12;  # 12*24*days = 12 intervals of 5 mins * 24 h * days
            x0 = 0.0; v0 = 0;
            m = 1  # unit of mass

            O = self.B * self.H
            # head loss coeff. includes flow separation and bottom friction
            fm = self.L * (f / self.L + self.Cd / self.H)

            # linearized loss term coefficient
            n0 = 8 * fm * self.A / (3 * np.pi * O * self.L)

            # eigenfrequency
            self.w0 = np.sqrt(g * O / self.L / self.A);
            print 'embayment eigen angular frequency %s=%f (rad/s)' % (omega_char, self.w0)

            freq0 = self.w0 / (2 * np.pi)
            print 'embayment eigen frequency f=%f (Hz),  n0=%f' % (freq0, n0)

            T0 = 1 / freq0  # sec
            print 'embayment eigen period T=%f (hours) = %f (min)' % (T0 / 3600, T0 / 60)



            t = np.linspace(0, tmax, nt);

            Fin = 0  # forcing
            R = 0  # Response
            for i in range(0, len(self.Amplitude)):
                freq = 1 / (self.Period[i] * 3600)
                self.w[i] = 2 * np.pi * freq



                Fin += self.Amplitude[i] * np.sin(self.w[i] * t + self.Phase[i])


                bay_ampl = self.amplitudef(self.Amplitude[i], self.w[i], self.w0, n0)

                self.X[i] = np.real(bay_ampl * np.exp(1j * self.w[i] * t))  # bay response oscillation function
                # for ii in range(0, len(self.X[i])):
                #    print self.X[i][ii]
                self.fwave[i] = np.real(self.Amplitude[i] * np.exp(1j * (self.w[i] * t)))  # forcing oscillation function
                # for ii in range(0, len(self.fwave[i])):
                #    print self.fwave[i][ii]

                self.c[i] = n0 * self.w[i] * np.abs(bay_ampl)  # damping effect
                self.k[i] = self.w0 ** 2 * m;  # elastic constant
                self.Fa[i] = self.k[i] * self.Amplitude[i]  # the forcing function
                self.phy[i] = np.arccos((1 - (self.w[i] / self.w0) ** 2) * bay_ampl / self.Amplitude[i])
                self.tsup[i] = self.phy[i] / self.w[i]  # suplementary period due to phase lag
                print "*********************************"
                print 'embayment amplitude=', bay_ampl
                print 'phase =%f ' % (self.phy[i])
                print 'response frequency=%f (Hz), angular freq = %f (rad) period= %f (h)' % (freq, self.w[i], 1 / freq / 3600)
                maxampl = self.max_amplification(self.Amplitude[i], n0)
                print 'embayment max amplit for T=%f (hours) Amplit = %f (m)  Max Ampl = %f (m)' % (self.Period[i], self.Amplitude[i], maxampl)
                print ''
                R += self.X[i]
            # end for
            return [t, self.X, self.c, self.k, self.w, x0, v0, R]
        # end Response

    def plotForcingResponse(self, t, printtitle = False, grid = False):
        '''
        Plot individual frequency responses
        '''
        if self.w0 == None:
            print "Error! Response not calculated yet."
            exit(0)

        ff, ax = plt.subplots(len(self.Amplitude))
        plt.subplots_adjust(hspace = 0.8)
        yFormatter = FormatStrFormatter('%.3f')

        for i in range(0, len(self.Amplitude)):
            nPoints = 1300
            ax[i].plot((t[0:nPoints] + self.tsup[i]) / 3600, self.X[i][0:nPoints])
            ax[i].set_xlabel('Time (h)').set_fontsize(22)
            ax[i].plot(t[0:nPoints] / 3600, self.fwave[i][0:nPoints], '-.r')

            ax[i].legend(['bay', 'lake'], fontsize = '18')
            if printtitle:
                title = 'Response embayment: %s - Forcing: a=%5.3f (m), T=%5.2f (h)' % (self.location_name, self.Amplitude[i], self.Period[i])
                ax[i].set_title(title)

            ax[i].set_ylabel('Displ. (m)').set_fontsize(22)
            ax[i].grid(grid)
            mn1 = np.min(self.X[i][0:nPoints])
            mn2 = np.min(self.fwave[i][0:nPoints])
            ma1 = np.max(self.X[i][0:nPoints])
            ma2 = np.max(self.fwave[i][0:nPoints])
            mn = min(mn1, mn2)
            ma = max(ma1, ma2)
            step = (ma - mn) / 3
            ax[i].yaxis.set_major_formatter(yFormatter)
            ax[i].set_yticks(np.arange(mn, ma + ma / 10., step))


        # end for


    def plotRespVsOmegaVarAmplit(self, printtitle = False, grid = False):
        # Plot the response |G(w)| versus frequency (omega)

        if self.w0 == None:
            print "Error! Response not calculated yet."
            exit(0)

        steps = 1000
        start = 0.0001
        ntimes = 3.5
        om = np.linspace(0.0001, self.w0 * ntimes, steps)

        m = 1  # m = mass
        ctr = 0
        Fa_sum = 0.
        # variable amplitude
        O = self.B * self.H
        # head loss coeff. includes flow separation and bottom friction
        fm = self.L * (f / self.L + self.Cd / self.H)
        n0 = 8 * fm * self.A / (3 * np.pi * O * self.L)

        eps = self.w0 / 8.

        fig = plt.figure(facecolor = 'w', edgecolor = 'k')
        legend = []
        if printtitle:
            title = 'Hypothetical Response for main forcings - Embayment: %s' % self.location_name
            plt.title(title).set_fontsize(20)

        plt.ylabel('Amplitude (m)').set_fontsize(22)
        xlabel = '%s/%s' % (omega, omega0)
        plt.xlabel(xlabel).set_fontsize(22)
        plt.grid(grid)
        plt.xticks(fontsize = 20)
        plt.yticks(fontsize = 20)

        for i in range(0, len(self.Amplitude)):

            bay_ampl = self.amplitudef(self.Amplitude[i], om, self.w0, n0)  # self.w[1], w0, n0)
            if abs(self.w0 - self.w[i]) < eps :
                plt.plot(om / self.w0, abs(bay_ampl), '-', lw = 4.5)
            else:
                plt.plot(om / self.w0, abs(bay_ampl), '--', lw = 2.5)

            lgnd = "T(%d)=%.3f   %s=%.3f" % (i + 1, self.Period[i], alpha0, self.Amplitude[i])
            legend.append(lgnd)

            plt.vlines(self.w[i] / self.w0, 0, np.max(abs(bay_ampl)), linestyles = 'dashed', lw = 1.5)
            ant = '%s$_%d$' % (omega, i + 1)
            delta = (ntimes * self.w0 - start) / steps
            j = int((self.w[i] - start) / delta)  # - ntimes * 2
            plt.annotate(ant, xy = (self.w[i] / self.w0, abs(bay_ampl[j])), xytext = (60, 10), \
                        arrowprops = dict(arrowstyle = '->', color = 'black'), size = 18, \
                        textcoords = 'offset points', ha = 'left', va = 'center', bbox = dict(fc = 'white', ec = 'none'))
        # end for
        # Superimposed response
        # plt.plot(om / self.w0, abs(GT))

        plt.legend(legend, fontsize = '18')


    def plotRespVsOmegaVarFric(self, printtitle = False, grid = False):
        '''Plot the response |G(w)| versus frequency (omega)
           for various levels of friction
        '''

        if self.w0 == None:
            print "Error! Response not calculated yet."
            exit(0)

        steps = 1000
        start = 0.0001
        ntimes = 4
        om = np.linspace(0.0001, self.w0 * ntimes, steps)


        m = 1  # m = mass
        ctr = 0

        Nfric = 3
        ls = ['--', '-', '-.']
        # variable friction
        for i in range(0, Nfric):
            self.G[i] = self.fourierODE(m, self.c[0] * (i + 1) / 2., self.k[i], self.Fa[0], om)

            # fric term like parallel circuits
            # ctr += 1 / self.c[i]
            # Fa_sum += self.Fa[i]
        # end for

        # ct = 1 / ctr
        # GT = fourierODE(m, ct, k, Fa_sum, om);

        fig = plt.figure(facecolor = 'w', edgecolor = 'k')
        legend = []
        if printtitle:
            title = 'Hypothetical response for variable friction - Embayment: %s' % self.location_name
            plt.title(title).set_fontsize(18)

        plt.ylabel('Amplitude (m)').set_fontsize(22)
        xlabel = '%s/%s' % (omega, omega0)
        plt.xlabel(xlabel).set_fontsize(22)
        plt.grid(grid)
        plt.xticks(fontsize = 20)
        plt.yticks(fontsize = 20)

        for i in range(0, Nfric):
            plt.plot(om / self.w0, abs(self.G[i]), ls[i], lw = 3)
            lgnd = 'fric=c*%2.1f' % ((i + 1) / 2.0)
            legend.append(lgnd)

        # end for
        # plt.plot(om / w0, abs(GT))
        plt.legend(legend, fontsize = '18')


    def plotPhaseVsOmega(self, printtitle = False, grid = False):
        '''Plot the Phase diagram
            variable amplitude
        '''

        if self.w0 == None:
            print "Error! Response not calculated yet."
            exit(0)

        fricsize = 3
        ls = ['-', '--', '-.']

        PHI = np.zeros(fricsize, dtype = np.ndarray)
        steps = 1000
        start = 0.0001
        ntimes = 4
        om = np.linspace(0.0001, self.w0 * ntimes, steps)


        O = self.B * self.H;
        # head loss coeff. includes flow separation and bottom friction
        fm = self.L * (f / self.L + self.Cd / self.H);

        # linearized loss term coefficient
        n0 = 8 * fm * self.A / (3 * np.pi * O * self.L)


        for i in range(0, fricsize):
            PHI[i] = self.phaseODE(n0 * (i + 1), self.w0, self.Amplitude[0], om)
        # end for

        fig = plt.figure(facecolor = 'w', edgecolor = 'k')
        legend = []
        T0 = 2 * np.pi / self.w0 / 3600
        T = 2 * np.pi / om / 3600

        if printtitle:
            title = 'Phase lag - Embayment: %s' % self.location_name
            plt.title(title).set_fontsize(18)

        plt.ylabel('Phase (rad)').set_fontsize(22)
        xlabel = '%s/%s' % (omega, omega0)
        plt.xlabel(xlabel).set_fontsize(22)
        plt.grid(grid)
        plt.xticks(fontsize = 20)
        plt.yticks(fontsize = 20)

        for i in range(0, fricsize):
            plt.plot(T0 / T, PHI[i], ls[i], lw = (fricsize + 2) - i)
            lgnd = 'fric=c*%d' % (i + 1)
            legend.append(lgnd)
        # end for

        plt.legend(legend, loc = 4, fontsize = '18')


    def plotRespVsOmegaVarArea(self, printtitle = False, grid = False):
        '''Plot the response |G(w)| versus frequency (omega)
           for various embayment areas
        '''

        if self.w0 == None:
            print "Error! Response not calculated yet."
            exit(0)

        m = 1  # m = mass
        steps = 1000
        start = 0.0001
        ntimes = 3


        O = self.B * self.H;

        # head loss coeff. includes flow separation and bottom friction
        fm = self.L * (f / self.L + self.Cd / self.H);

        if ntimes == 3:
            ls = ['--', '-', '-.']
        else :
            ls = ['--', ':', '-', ':', '.-']
        fig = plt.figure(facecolor = 'w', edgecolor = 'k')
        legend = []
        if printtitle:
            title = 'Hypothetical response for variable area - Embayment: %s' % self.location_name
            plt.title(title).set_fontsize(18)

        plt.ylabel('Amplitude (m)').set_fontsize(22)
        xlabel = '%s/%s' % (omega, omega0)
        plt.xlabel(xlabel).set_fontsize(22)
        plt.grid(grid)
        plt.xticks(fontsize = 20)
        plt.yticks(fontsize = 20)

        # variable friction
        for i in range(0, ntimes):
            if ntimes == 3:
                if i == 0:
                    lgnd = "Area/6"
                    A = self.A / 6
                if i == 1:
                    lgnd = "Area=%d (m$^2$)" % self.A
                    A = self.A
                if i == 2:
                    lgnd = "Area*6"
                    A = self.A * 6

            elif ntimes == 5:
                if i == 0:
                    lgnd = "Area/3"
                    A = self.A / 3
                if i == 1:
                    lgnd = "Area/1.5"
                    A = self.A / 1.5
                if i == 2:
                    lgnd = "Area=%d (m$^2$)" % self.A
                    A = self.A
                if i == 3:
                    lgnd = "Area*1.5"
                    A = self.A * 1.5
                if i == 4:
                    lgnd = "Area*3"
                    A = self.A * 3
                # eigenfrequency
            # end if

            w0 = np.sqrt(g * O / self.L / A);

            om = np.linspace(0.0001, w0 * ntimes, steps)

            n0 = 8 * fm * A / (3 * np.pi * O * self.L)

            bay_ampl = self.amplitudef(self.Amplitude[1], om, w0, n0)  # self.w[1], w0, n0)

            # k = w0 ** 2 * m;  # elastic constant
            # c = n0 * self.w[0] * np.abs(bay_ampl)  # damping effect
            # Fa = k * self.Amplitude[1]  # the forcing function
            # ampl = self.fourierODE(m, c, k, Fa, om)

            plt.plot(om / w0, abs(bay_ampl), ls[i], lw = (ntimes + 2) - i)
            legend.append(lgnd)
        # end for




        # end for
        # plt.plot(om / w0, abs(GT))
        plt.legend(legend, fontsize = '18')

    def plotRespVsOmegaVarMouth(self, printtitle = False, grid = False):
        '''Plot the response |G(w)| versus frequency (omega)
           for various mouth areas
        '''

        if self.w0 == None:
            print "Error! Response not calculated yet."
            exit(0)

        m = 1  # m = mass
        steps = 1000
        start = 0.0001
        ntimes = 3


        O = self.B * self.H;

        # head loss coeff. includes flow separation and bottom friction
        fm = self.L * (f / self.L + self.Cd / self.H);

        if ntimes == 3:
            ls = ['--', '-', '-.']
        else :
            ls = ['--', ':', '-', ':', '.-']

        fig = plt.figure(facecolor = 'w', edgecolor = 'k')
        legend = []

        if printtitle:
            title = 'Hypothetical response for variable area - Embayment: %s' % self.location_name
            plt.title(title).set_fontsize(18)

        plt.ylabel('Amplitude (m)').set_fontsize(22)
        xlabel = '%s/%s' % (omega, omega0)
        plt.xlabel(xlabel).set_fontsize(22)
        plt.grid(grid)
        plt.xticks(fontsize = 20)
        plt.yticks(fontsize = 20)

        # variable friction

        for i in range(0, ntimes):
            if ntimes == 3:
                if i == 0:
                    lgnd = "Mouth area/6"
                    CO = O / 6
                if i == 1:
                    lgnd = "Mouth area=%d (m$^2$)" % O
                    CO = O
                if i == 2:
                    lgnd = "Mouth Area*6"
                    CO = O * 6
            elif ntimes == 5:
                if i == 0:
                    lgnd = "Mouth area/3"
                    CO = O / 3
                if i == 1:
                    lgnd = "Mouth area/1.5"
                    CO = O / 1.5
                if i == 2:
                    lgnd = "Mouth area=%d (m$^2$)" % O
                    CO = O
                if i == 3:
                    lgnd = "Mouth Area*1.5"
                    CO = O * 1.5
                if i == 4:
                    lgnd = "Mouth Area*3"
                    CO = O * 3

            # eigenfrequency
            w0 = np.sqrt(g * CO / self.L / self.A);
            om = np.linspace(0.0001, w0 * ntimes, steps)
            n0 = 8 * fm * self.A / (3 * np.pi * CO * self.L)
            bay_ampl = self.amplitudef(self.Amplitude[1], om, w0, n0)  # self.w[1], w0, n0)

            # k = w0 ** 2 * m;  # elastic constant
            # c = n0 * self.w[1] * np.abs(bay_ampl)  # damping effect
            # Fa = k * self.Amplitude[1]  # the forcing function
            # ampl = self.fourierODE(m, c, k, Fa, om)

            plt.plot(om / w0, abs(bay_ampl), ls[i], lw = (ntimes + 2) - i)
            legend.append(lgnd)
        # end for




        # end for
        # plt.plot(om / w0, abs(GT))
        plt.legend(legend, fontsize = '18')

    def plotModelLines(self, T = 1.5, lw = 1, ls = '-'):
        steps = 1000
        start = 0.01

        H = 1.5
        stop = 40
        Amplitude = 0.1
        Period = T
        L = 2000
        Cd = 0.0032
        b = np.linspace(start , stop, steps)
        aa = [5000, 30000, 65000, 150000, 500000, 1000000]
        # aa = [180000]

        bay_ampl = np.zeros(steps)
        legend = []


        plt.xscale('log')
        p = 0
        for A in aa:
            for j in range(0, steps):
                O = b[j] * H

                # head loss coeff. includes flow separation and bottom friction
                fm = L * (f / L + Cd / H)

                # linearized loss term coefficient
                n0 = 8 * fm * A / (3 * np.pi * O * L)

                # eigenfrequency
                w0 = np.sqrt(g * O / L / A)
                # print 'embayment eigen angular frequency %s=%f (rad)' % (omega_char, w0)

                freq0 = w0 / (2 * np.pi)
                # print 'embayment eigen frequency f=%f (Hz)' % freq0

                T0 = 1 / freq0  # sec
                # print 'embayment eigen period T=%f (hours) = %f (min)' % (T0 / 3600, T0 / 60)

                freq = 1. / (Period * 3600)
                w = 2 * np.pi * freq

                bay_ampl[j] = self.amplitudef(Amplitude, w, w0, n0)
                # print "mouth area=%f  - bay amplit=%f" % (O, bay_ampl[j])
            # end for j

            plt.semilogx(b * H, bay_ampl / Amplitude, lw = lw, ls = ls)
            p += 1
            ar = A / 10000
            if ar < 0.1 : ar = 0.1
            txt = "A = %.1f ha" % (ar)
            legend.append(txt)
            # print "*** A = %s ***" % txt
        # end for jj

        plt.ylabel('Relative Amplitude').set_fontsize(22)
        xlabel = 'Mouth area ($m^2$)'
        plt.xlabel(xlabel).set_fontsize(22)
        plt.legend(legend, loc = 2)
        plt.xticks(fontsize = 20)
        plt.yticks(fontsize = 20)

        # end for A
    # end function

    def plotRespVsOmegaVarMouthCurves(self, printtitle = False, grid = False):
        '''Plot the response |G(w)| versus frequency (omega)
           for various mouth areas
        '''
        fig = plt.figure(facecolor = 'w', edgecolor = 'k')
        self.plotModelLines(T = 1.5, lw = 2, ls = '-')
        self.plotModelLines(T = 7.9, lw = 1, ls = ':')
        # lake Superior embayments

        ls = ['bo', 'g^', 'rs']
        path = "/home/bogdan/Documents/UofT/PhD/docear/projects/Papers-Written/Environmental_Fluid_Mechanics/support_data"
        filename = "trebitz_resp.txt"
        filename2 = "trebitz_resp_no_lagoon.txt"

        [MouthArea, RelativeAmplit, Name, Area] = tg.readFile(path, filename)
        plt.plot(MouthArea, RelativeAmplit, ls[0])
        xmax = np.max(MouthArea)
        ymax = np.max(RelativeAmplit)
        xmin = np.min(MouthArea)
        ymin = np.min(RelativeAmplit)
        for i in range(0, len(Area)):
            plt.annotate(Area[i], (MouthArea[i], RelativeAmplit[i]), xytext = (xmax / 8., ymax / 8.), \
                         textcoords = 'offset points', ha = 'left', va = 'center', size = 18, bbox = dict(fc = 'white', ec = 'none'))
        plt.grid(grid)

        # statistics
        x = np.array(MouthArea)
        y = np.array(RelativeAmplit)
        [r2, slope, intercept, r_value, p_value, std_err] = ustats.rsquared(x, y)
        ustats.plot_regression(x, y, slope, intercept, point_labels = None, x_label = "Mouth area (m$^2$)", y_label = "Relative amplitude", title = None, \
                    r_value = r_value, p_value = p_value, fontsize = 22)

        # for no outliers
        [MouthArea2, RelativeAmplit2, Name2, Area2] = tg.readFile(path, filename2)
        x2 = np.array(Area2)
        y2 = np.array(RelativeAmplit2)
        [r2_2, slope2, intercept2, r_value2, p_value2, std_err2] = ustats.rsquared(x2, y2)

        x = np.array(Area)
        y = np.array(RelativeAmplit)
        [r2, slope, intercept, r_value, p_value, std_err] = ustats.rsquared(x, y)
        # pass the regression line params for no outliers
        ustats.plot_regression(x, y, slope2, intercept2, point_labels = None, x_label = "Area (ha)", y_label = "Relative amplitude", title = None, \
                    r_value = r_value2, p_value = p_value2, fontsize = 22)

    # end def

    def plotDimensionlessResponse(self, bbox = None, printtitle = False, grid = False):


        embayments = {'FMB' : {'A':850000., 'B':25. , 'H':1., 'L':130.,
                       'Period':[12.4, 5.2, 1.28, 0.8, 0.5, 0.36] ,  # h
                       'Amplitude':[0.034, 0.022, 0.017, 0.023, 0.021, 0.022],  # m
                       'Amplitude_bay':[0.024, 0.02, 0.014, 0.012, 0.0045, 0.002],  # m
                       'Phase':[5, 22, -15, 39, -4.6, 0],  # rad
                       'CD':0.0032},
              'Tob-IBP' : {'A':145000., 'B':140. , 'H':2.143, 'L':570.,
                       'Period':[16.8 / 60, 12.0 / 60, 8.0 / 60] ,  # min
                       'Amplitude':[0.02, 0.018, 0.016],  # m
                       'Amplitude_bay':[0.09, 0.043, 0.058],  # m
                       'Phase':[0, 0, 0],  # rad
                       'CD':0.0032},
              'Tob-CIH' : {'A':64000., 'B':56. , 'H':1.9, 'L':175.,
                       'Period':[16.8 / 60, 12.0 / 60, 9.2 / 60] ,  # h
                       'Amplitude':[0.02, 0.018, 0.014],  # m
                       'Amplitude_bay':[0.025, 0.078, 0.037],  # m
                       'Phase':[0, 0, 0],  # rad
                       'CD':0.0032}
        }

        Cd = 0.003;

        plt.figure()

        start = 0.0;
        stop = 3.5;
        step = 0.02;
        A_stop = 52;
        A_start = 0.04;
        A_step = 5;

        maxidx = (stop - start) / step

        arel = np.zeros((200, 200))
        ixa = 0
        steps = (stop - start) / step
        ww = np.linspace(start , stop, steps)
        A = A_start
        while A < A_stop:
            ixw = 1
            for w in ww:
                arel[ixa, ixw] = self.dl_amplitudef(A, w) / A
                ixw += 1
            # end
            ixa += 1
            A = A * 3
        # end while

        ixa = 0
        w = np.linspace(start, stop, (stop - start) / step)
        wint = np.linspace(start, stop, (stop - start) / step * 4)
        linestyle = ['r-', 'g:', 'b--', 'k-.', 'y-', 'c--', 'm:']
        marker = ['o', '*', '^', 'd', 's', '+', 'o']

        A = A_start
        cellgr = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']

        legend = []
        while A < A_stop:
           ac = arel[ixa, :]
           colr = np.mod(ixa, 6)
           ls = linestyle[colr]
           mk = marker[colr]
           plt.plot(w, ac[:len(w)], ls, lw = 2 + 0.4 * ixa)
           gg = 'forcing=%5.2f' % A
           cellgr[ixa] = gg
           legend.append(gg)
           ixa += 1
           A = A * 3
        # end
        if printtitle:
            plt.title('Amplification factor for a dimensionless forcing')
        xlabel = 'Dimensionless Frequency (%s/%s)' % (omega, omega0)
        plt.xlabel(xlabel, fontsize = 22)
        ylabel = 'Relative Dimensionless Amplitude (%s/%s)' % (alpha, alphae)
        plt.ylabel(ylabel, fontsize = 22)
        plt.grid(grid, which = 'major', axis = 'y')
        plt.legend(legend)
        plt.xticks(fontsize = 20)
        plt.yticks(fontsize = 20)

        # dimesionless values
        pmax = 0
        for key, value in embayments.iteritems():
            pmax += len(value['Period'])
        # end for
        ratioMeas = np.zeros(pmax, dtype = np.float)
        ratioCalc = np.zeros(pmax, dtype = np.float)
        ratioMeasNoOutl = np.zeros(pmax, dtype = np.float)
        ratioCalcNoOutl = np.zeros(pmax, dtype = np.float)
        outliers_emb = ['TOB-IBP', 'TOB-IBP']
        outliers_freq = ['0.13', '0.20']

        stxt = np.zeros(pmax, dtype = np.dtype('a14'))


        j = 0
        for key, value in embayments.iteritems():

            name = key
            print "embayment: %s" % name

            if bbox:
                bbox_props = dict(boxstyle = "square,pad=0.3", fc = "white", ec = "b", lw = 1)
            else:
                bbox_props = None

            dict = value
            A = dict['A']
            B = dict['B']
            H = dict['H']
            L = dict['L']
            Period = dict['Period']
            Amplitude = dict['Amplitude']
            Amplitude_bay = dict['Amplitude_bay']
            Phase = dict['Phase']
            CD = dict['CD']

            O = B * H
            fm = L * (f / L + CD / H)
            i = 0
            ko = 0
            for T in Period:
                k = j * len(embayments) + i
                DAmplE = A * fm / O / L * Amplitude[i]
                DAmplBay = A * fm / O / L * Amplitude_bay[i]
                w0 = np.sqrt(g * O / L / A)
                freq = 1 / (T * 3600)
                w = freq * 2 * np.pi
                # dimensionless freq
                wp = w / w0

                # measured forcing
                ratioMeas[k] = DAmplBay / DAmplE
                print "%d) rmeas:%f" % (k, ratioMeas[k]),
                plt.plot(wp, ratioMeas[k], marker = marker[i], markersize = 13)
                txt = '%s_M(%.2f h)' % (name, T)
                plt.text(wp + 0.02, ratioMeas[k], txt, ha = 'left', va = 'center', bbox = bbox_props, fontsize = 15)


                # draw veritical line at omega zero

                # calculated forcing
                DCalcAmplBay = self.dl_amplitudef(DAmplE, wp)
                ratioCalc[k] = DCalcAmplBay / DAmplE
                print "  rcalc:%f" % ratioCalc[k]
                plt.plot(wp, ratioCalc[k], marker = marker[i], markersize = 13)
                txt = '%s_C(%.2f h)' % (name, T)
                plt.text(wp + 0.02, ratioCalc[k], txt, ha = 'left', va = 'center', bbox = bbox_props, fontsize = 15)

                stxt[k] = '%s(%.2f)' % (name, T)
                plt.vlines(wp, 0, max(ratioMeas[k], ratioCalc[k]) + 0.03, linestyles = ':')

                o = 0
                bOutlier = False
                for e in outliers_emb:
                    oe = e + outliers_freq[o]
                    if stxt[k] == oe:
                        bOutlier = True
                        break
                    o += 1
                # end for

                # add to list if not outlier
                if  not bOutlier:
                    ratioMeasNoOutl[ko] = ratioMeas[k]
                    ratioCalcNoOutl[ko] = ratioCalc[k]
                    ko += 1

                i += 1
            # end for
            j += 1
        # end for in embayments

        # plot a regression to estimate the accuracy of model prediction
        # statistics

        [r2, slope, intercept, r_value, p_value, std_err] = ustats.rsquared(ratioMeasNoOutl, ratioCalcNoOutl)
        ustats.plot_regression(ratioMeas, ratioCalc, slope, intercept, point_labels = stxt, x_label = "Meas. Relative Amplit", y_label = "Calc. Relative amplitude", title = None, \
                               r_value = r_value, p_value = p_value, fontsize = 22)



