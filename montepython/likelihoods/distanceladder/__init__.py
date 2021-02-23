import os
from montepython.likelihood_class import Likelihood
import math as m
import statistics as s
from scipy import stats
import scipy.linalg as la
import numpy as np
from scipy.integrate import quad


def lin_reg(x,y):

    #length of data set
	n = len(x)

    #summing independent variable
	x_sum = sum(x)
    #summing dependent variable
	y_sum = sum(y)

    #mean of independent variable
	x_mean = s.mean(x)

    #mean of dependent variable
	y_mean= s.mean(y)

    #sum of x squared
	x_sqr = []
	for i in range(len(x)):
		x_temp = x[i]**2
		x_sqr.append(x_temp)
	x_sqr_sum = sum(x_sqr)

    #sum of y squared
	y_sqr = []
	for i in range(len(y)):
		y_temp = y[i]**2
		y_sqr.append(y_temp)
	y_sqr_sum = sum(y_sqr)

    #sum of xy product
	xy_prod = []
	for i in range(len(y)):
		xy_temp = y[i]*x[i]
		xy_prod.append(xy_temp)
	xy_prod_sum = sum(xy_prod)

    #numerator and denominator of slope estimate
	S_xx = x_sqr_sum - (x_sum**2/n)
	S_xy = xy_prod_sum - (x_sum*y_sum/n)

    #slope estimate
	B_1 = S_xy/S_xx

    #intercept estimate
	B_0 = y_mean - B_1*x_mean

	return B_0, B_1

#simple linear regression with fixed slope and error on slope
def lin_reg_fixed_slope(x,y,m,dm,dx,dy):
    
	B_0 = np.mean(y-m*x)
	B_1 = m
    
	dB0 = np.sqrt((1/len(x)))*np.sqrt(np.sum(np.power(dy,2))+np.sum(np.power(m*x,2)*(np.power(dm/m,2)+np.power(dx/x,2))))
	dB1 = dm

	return B_0, B_1, dB0, dB1

# linear regression using error as a weighting scheme, fixing slope and slope error

def weighted_fixed_slope(x,y,m,dm,dx,dy):
    #wx = 1/dx^2
    #wy = 1/dy^2
	w = 1/(dx**2+dy**2)
    
	ybar = sum(w*y)/sum(w)
	xbar = sum(w*x)/sum(w)
    
	B0 = ybar - m*xbar

	r = y - (B0 +m*x)
	wr = np.sqrt(w)*r
	n = len(x)

	SE_wr = np.sqrt(sum(wr**2)/(n-2))
	dB0 = np.sqrt((SE_wr**2/sum(w))+dm*xbar**2)
	B1 = m
	dB1 = dm

	return B0, B1, dB0, dB1

#york linear regression

# York correction to linear regression including error in both x and y
# https://aapt.scitation.org/doi/abs/10.1119/1.1632486

def york_fit(x,y,sigma_x,sigma_y,r,tol,n_max):
#make sure inputs are a numpy array
	#if the error is 0, replace with something very very small to
	# to prevent nan
	sigma_x[sigma_x == 0] = 10**-15
	sigma_y[sigma_y == 0] = 10**-15

#define an array which tracks the changes in slope, B_1
	b_hist = np.ones(n_max)

#1) choose an approximate initial value for the slope, b
	# -> simple linear regression
# B_0 is intercept, B_1 is slope from simple linear regression
	[B_0_simple, B_1_simple] = lin_reg(x,y)
	b_hist[0] = B_1_simple
	B_0 = B_0_simple
	B_1 = B_1_simple

#2) determine the weights omega of each point for both x and y
	# usually 1/sigma where sigma is the error associated with x and y
	# at the i'th point

	omega_x = 1/np.square(np.array(sigma_x))
	omega_y = 1/np.square(np.array(sigma_y))

#3) use these weights with B_1 and the correlation r (if any) to
	# evaluate W_i for each point
	alpha = np.sqrt(omega_x*omega_y)
#6) calculate B_1_new until the difference between B_1_new and B_1 is
	# less than the tolerance provided
	counter = 1
	while counter < n_max:
		W = (omega_x*omega_y)/(omega_x + (B_1**2)*omega_y - 2*B_1*r*alpha)
    
#4) use the observed points and W to calculate x_bar and y_bar from
    # from which U V and beta can be evaluated for each point
    
		x_bar = sum(W*x)/sum(W)
		y_bar = sum(W*y)/sum(W)
    
		U = x - x_bar
		V = y - y_bar
		beta = W*((U/omega_y)+(B_1*V/omega_x)-(B_1*U+V)*(r/alpha))
    
#5) use W U V and beta to calculate a new estimate of B_1

		B_1_new = sum(W*beta*V)/sum(W*beta*U)
		b_hist[counter] = B_1_new

		if(abs(B_1_new-B_1)< tol):
			B_1 = B_1_new
			break

		counter += 1
		B_1 = B_1_new

#7) using the final value of B_1, x_bar, y_bar, calculate B_0
    
	B_0 = y_bar - B_1*x_bar
    
#8) for each point x and y, calculate the adjusted values
	x_adj = x_bar + beta
	y_adj = y_bar + B_1*beta
    
#9) use x_adj and W to calc x_bar_adj and u abd v
	x_bar_adj = sum(W*x_adj)/sum(W)
    #y_bar_adj = sum(W*y_adj)/sum(W)
    
	u = x_adj - x_bar_adj
    #v = y_adj - y_bar_adj
    
#10) use W x_bar and u to calculate sigma_a and sigma_b
    
	var_b = 1/(sum(W*u**2))
	var_a = 1/sum(W)+(x_bar**2)*var_b
    
	sigma_a_new = np.sqrt(var_a)
	sigma_b_new = np.sqrt(var_b)

    
	return B_0, B_1, sigma_a_new, sigma_b_new, b_hist, B_0_simple, B_1_simple



#######################################################################################
#CLASS DEFINITIONS OF STEPS OF THE DISTANCE LADDER#
#######################################################################################

# This class defines the structure in which Anchors with known distances 
#and contain cepheids are imported

class Anchor:
	"This class defines a structure which holds data for objects that have geometric distance measurements, and cepheid variables."

	def __init__(self,Name='',Dist=0,dDist=0):

		self.Name = Name
		self.Dist = Dist
		self.dDist = dDist
		self.mu = 5*np.log10(self.Dist)-5
		self.dmu = 5*np.log10(np.exp(1))*self.dDist/self.Dist

	def Compute_abs_ceph_mag(self,period,dperiod,mh,dmh):
		r = 0
		tol = 10**-15
		n = 20
		[B_0, B_1, sigma_B_0, sigma_B_1, b_save, B_0_simple, B_1_simple] = york_fit(period,mh,dperiod,dmh,r,tol,n)

		self.Mceph = B_0 - self.mu
		self.dMceph = np.sqrt(np.power(sigma_B_0,2)+np.power(self.dmu,2))



# This class defines the structure in which the cephied data is 
#imported, and the DM calculated to those cephieds

class Ceph_data:
	"This class creates a structure which holds cepheid data for a given host"

	def __init__(self,Host='',ID='',Period=0,V=0,dV=0,I=0,dI=0,NIR=0,dNIR=0,OH=0):

		self.Host = Host
		self.ID = ID
		self.Period = Period
		self.NIR = NIR
		self.dNIR = dNIR
		self.V = V
		self.dV = dV
		self.I = I
		self.dI = dI
		# R value is a correlation coeffecient, forced to be the same 
		#as what is used in previous analysis
		self.R = 0.386
		self.mh = NIR - self.R*(V-I)
		self.dmh = np.sqrt(np.power(dNIR,2)+self.R*np.power(dV,2)+self.R*np.power(dI,2))

	def proto_Compute_mu(self,mh,dmh,period,dperiod,Mceph,dMceph,slope,dslope):

		[B0, B_1, dB0, dB1] = weighted_fixed_slope(period,mh,slope,dslope,dperiod,dmh)

		self.mu = B0 - Mceph
		self.dmu = np.sqrt(np.power(dB0,2)+np.power(dMceph,2))

# This class defines the structure in which the SN which are 
#found with cephieds are imported

class Local_SN_data:
	"This class creates a structure which holds SN data for a given host."

	def __init__(self,Host='',ID='',m=0,dm=0):

		self.Host = Host
		self.ID = ID
		self.m = m
		self.dm = dm

	def Compute_abs_sn_mag(self,m,dm,mu,dmu):

		x = mu
		y = m
		xerror = dm
		yerror = dmu
		[Msn, B1, dMsn, sigma_B1] = weighted_fixed_slope(x,y,1,0,xerror,yerror)
		self.Msn = Msn
		self.dMsn = dMsn

# This class defines the structure in which hubble flow SN are imported

class Hubble_SN_data:
	"This class creates a structure which holds SN data in the hubble flow."
	
	def __init__(self,ID='',z=0,dz=0,m=0,dm=0):

		self.ID = ID
		self.m = m
		self.dm = dm
		self.z = z
		self.dz = dz

	def Compute_hubble_mu(self,m,dm,Msn,dMsn):
		self.mu = m - Msn
		self.dmu = np.sqrt(np.power(dm,2)+np.power(dMsn,2))

class distanceladder(Likelihood):

	# initialization routine. Here we will establish the subclasses needed to calculate the 
	#attributes of the distance ladder, up until the distance modulus calculation of 
	#hubble flow SN

	def __init__(self, path, data, command_line):

		#initialization of Likelihood class
		Likelihood.__init__(self,path,data,command_line)

				#simple linear regression used by Yorkfit for initial parameter estimation
		

##########################################################################################
#TABLE READERS#
##########################################################################################

		def anchor_reader(file,index_array,header_length,delim):

			base_dir = self.data_directory
		    
		    #stable method to read in tabular data
			file = open(base_dir + file)
			table = file.readlines()
			file.close()
		    
		    #defining the length of the actual data of the table
			i = len(table)-header_length
		    
		    #preallocating the arrays for memory
			host_list = []
			dist_np = np.zeros(i)
			ddist_np = np.zeros(i)
		    
			lc = 0
		    
			for line in table:
		    
				lc += 1
				i = lc - header_length - 1
				data = line.strip('\n').split(delim)

				if lc>header_length:
					if index_array[0] is not np.NaN:
						host_list.append(data[index_array[0]])
					else:
						host_list.append(np.NaN)
				
					if index_array[1] is not np.NaN:
						dist_np[i] = data[index_array[1]]
					else:
						dist_np[i] = np.NaN
				
					if index_array[2] is not np.NaN:
						ddist_np[i] = data[index_array[2]]
					else:
						ddist_np[i] = np.NaN
				
			name = []
			for a in range(len(host_list)):
				name.append([host_list[a],dist_np[a],ddist_np[a]])
				        
			return name
		def ceph_table_reader(file,index_array,header_length,delim):
		    #file(string): location of table wished to be read in
		    #index_array(array): array containing the column index of the 
			#following attributes:
			#host,ID,period,V,dV,I,dI,NIR,dNIR,OH
			# if attribute does not occur in table, put -1
			#host: index of host column in table
			    # list, strings
			#ID: index of ID column in table
			    # list, strings
			#period: index of period column in table
			    # np array, float
			# the remainder of entries are the index of said variable in table
			    # all are np array's, with float values
		    #header_length(int): line number of last row of header
		    #name(string):user desired prefix for data
			# name_host, name_ID, etc
		    #cc(string): character which splits your data
		    
		    #All data should be located in this parent folder
			base_dir = self.data_directory
		    
		    #stable method to read in tabular data
			file = open(base_dir + file)
			table = file.readlines()
			file.close()
		    
		    #defining the length of the actual data of the table
			i = len(table)-header_length
		    
		    #preallocating the arrays for memory
			host_list = []
			ID_list = []
			period_np = np.zeros(i)
			V_np = np.zeros(i)
			dV_np = np.zeros(i)
			I_np = np.zeros(i)
			dI_np = np.zeros(i)
			NIR_np = np.zeros(i)
			dNIR_np = np.zeros(i)
			OH_np = np.zeros(i)
		    
			lc = 0
		    
			for line in table:
		    
				lc += 1
				i = lc - header_length - 1
				data = line.strip('\n').split(delim)

				if lc>header_length:
					if index_array[0] is not np.NaN:
						host_list.append(data[index_array[0]])
					else:
						host_list.append(np.NaN)
				
					if index_array[1] is not np.NaN:
						ID_list.append(data[index_array[1]])
					else:
						ID_list.append(np.NaN)
				
					if index_array[2] is not np.NaN:
						period_np[i] = data[index_array[2]]
					else:
						period_np[i] = np.NaN
				
					if index_array[3] is not np.NaN:
						V_np[i] = data[index_array[3]]
					else:
						V_np[i] = np.NaN
				
					if index_array[4] is not np.NaN:
						dV_np[i] = data[index_array[4]]
					else:
						dV_np[i] = np.NaN
				    
					if index_array[5] is not np.NaN:
						I_np[i] = data[index_array[5]]
					else:
						I_np[i] = np.NaN
				
					if index_array[6] is not np.NaN:
						dI_np[i] = data[index_array[6]]
					else:
						dI_np[i] = np.NaN
				
					if index_array[7] is not np.NaN:
						NIR_np[i] = data[index_array[7]]
					else:
						NIR_np[i] = np.NaN
				
					if index_array[8] is not np.NaN:
						dNIR_np[i] = data[index_array[8]]
					else:
						dNIR_np[i] = np.NaN
				
					if index_array[9] is not np.NaN:
						OH_np[i] = data[index_array[9]]
					else:
						OH_np[i] = np.NaN

				name = []
			for a in range(len(host_list)):
				name.append([host_list[a],ID_list[a],period_np[a],V_np[a],dV_np[a],I_np[a],dI_np[a],NIR_np[a],dNIR_np[a],OH_np[a]])
				        
			return name

		# reads in local SN data
		def local_sn_table_reader(file,index_array,header_length,delim):
		    
		    #All data should be located in this parent folder
			base_dir = self.data_directory
		    
		    #stable method to read in tabular data
			file = open(base_dir + file)
			table = file.readlines()
			file.close()
		    
		    #defining the length of the actual data of the table
			i = len(table)-header_length
		    
		    #preallocating the arrays for memory
			host_list = []
			ID_list = []
			m_np = np.zeros(i)
			dm_np = np.zeros(i)
		    
			lc = 0
		    
			for line in table:
		    
				lc += 1
				i = lc - header_length - 1
				data = line.strip('\n').split(delim)
	
				if lc>header_length:
				
					if index_array[0] is not np.NaN:
						host_list.append(data[index_array[0]])
					else:
						host_list.append(np.NaN)
				
					if index_array[1] is not np.NaN:
						ID_list.append(data[index_array[1]])
					else:
						ID_list.append(np.NaN)
				
					if index_array[2] is not np.NaN:
						m_np[i] = data[index_array[2]]
					else:
						m_np[i] = np.NaN
				
					if index_array[3] is not np.NaN:
						dm_np[i] = data[index_array[3]]
					else:
						dm_np[i] = np.NaN
				
			name = []
			for a in range(len(host_list)):
				name.append([host_list[a],ID_list[a],m_np[a],dm_np[a]])
				        
			return name


		def hubble_sn_table_reader(file,index_array,header_length,delim):
		    #host,ID,z_cmb,dz_cmb,m,dm

		    #All data should be located in this parent folder
			base_dir = self.data_directory
		    
		    #stable method to read in tabular data
			file = open(base_dir + file)
			table = file.readlines()
			file.close()
		    
		    #defining the length of the actual data of the table
			i = len(table)-header_length
		    
		    #preallocating the arrays for memory
			ID_list = []
			z_cmb_np = np.zeros(i)
			dz_cmb_np = np.zeros(i)
			m_np = np.zeros(i)
			dm_np = np.zeros(i)
		    
			lc = 0
		    
			for line in table:
		    
				lc += 1
				i = lc - header_length - 1
				data = line.strip('\n').split(delim)

				if lc>header_length:
				
					if index_array[0] is not np.NaN:
						ID_list.append(data[index_array[0]])
					else:
						ID_list.append(np.NaN)
				
					if index_array[1] is not np.NaN:
						z_cmb_np[i] = data[index_array[1]]
					else:
						dz_cmb_np[i] = np.NaN
				
					if index_array[2] is not np.NaN:
						dz_cmb_np[i] = data[index_array[2]]
					else:
						dz_cmb_np[i] = np.NaN
				
					if index_array[3] is not np.NaN:
						m_np[i] = data[index_array[3]]
					else:
						m_np[i] = np.NaN
				    
					if index_array[4] is not np.NaN:
						dm_np[i] = data[index_array[4]]
					else:
						dm_np[i] = np.NaN
			    
			    
			name = []
			for a in range(len(ID_list)):
				name.append([ID_list[a],z_cmb_np[a],dz_cmb_np[a],m_np[a],dm_np[a]])
		    
			return name


		################################################################################################
#READ IN TABULAR DATA#
################################################################################################

		#read in the data from the tables
		file = '/distanceladder/anchor_data.txt'
		index_array = [0,1,2]
		header_length = 1
		delim = ' '

		anchor_dat = anchor_reader(file,index_array,header_length,delim)

		file = '/distanceladder/cepheid_data.txt'
		index_array = [0,1,2,3,4,5,6,7,8,9]
		header_length = 1
		delim = ' '

		HR16_ceph = ceph_table_reader(file,index_array,header_length,delim)


		# This reads in local SN data

		file = '/distanceladder/localsn_data.txt'
		index_array = [0,1,2,3]
		header_length = 1
		delim = ' '

		R16_local_sn = local_sn_table_reader(file,index_array,header_length,delim)

		# This block is where the hubble flow SN data will be loaded and organized
		# Pantheon
		# Steinhardt
		file = '/distanceladder/hubblesn_data.txt'
		index_array = [0,1,2,3,4]
		header_length = 1
		delim = ' '

		PS_sn = hubble_sn_table_reader(file,index_array,header_length,delim)

		


################################################################################################
#CONSTRUCT DATA DICTIONARIES#
################################################################################################

		# This takes the imported anchor data, and places it into an anchor 
		#data class instance

		# NGC4258 Megamaser
		# LMC DEB
		# MW parallax
		# M31 DEB
		anchor_dict = {}

		for i in range(len(anchor_dat)):
			key = anchor_dat[i][0]
			value = Anchor(anchor_dat[i][0],anchor_dat[i][1],anchor_dat[i][2])
			anchor_dict[key] = value 

		# This takes the imported cepheid data, creates a dictionary where 
		#the elements of the dictionary are instances
		# of the cephied class
		# for clarity the dictionary contains elements organized by host galaxy, 
		#each element containing all cephieds
		# in that host.
		hosts=[]
		for i in range(len(HR16_ceph)):
			hosts.append(HR16_ceph[i][0])
		hosts = np.unique(hosts)


		ceph_dict = {}

		for i in range(len(hosts)):
			temp=[]
		    
			for j in range(len(HR16_ceph)):
				if hosts[i] == HR16_ceph[j][0]:
					temp.append(HR16_ceph[j])
			    
			k = len(temp)
			host = []
			ID = []
			per = np.zeros(k)
			V = np.zeros(k)
			dV = np.zeros(k)
			I = np.zeros(k)
			dI = np.zeros(k)
			NIR = np.zeros(k)
			dNIR = np.zeros(k)
			OH = np.zeros(k)
			    
			key = hosts[i]
		    
			for l in range(len(temp)):
				host.append(temp[l][0])
				ID.append(temp[l][1])
				per[l] = temp[l][2]
				V[l] = temp[l][3]
				dV[l] = temp[l][4]
				I[l] = temp[l][5]
				dI[l] =  temp[l][6]
				NIR[l] = temp[l][7]
				dNIR[l] = temp[l][8]
				OH[l] = temp[l][9]
		
		
			value = Ceph_data(host,ID,per,V,dV,I,dI,NIR,dNIR,OH)
			ceph_dict[key] = value



		# This takes the imported local SN data, creates a diction 
		#where where the elements of the dictionary are instances
		# of the local SN class

		hosts=[]
		for i in range(len(R16_local_sn)):
			hosts.append(R16_local_sn[i][0])
		hosts = np.unique(hosts)

		local_sn_dict = {}

		for i in range(len(hosts)):
			temp=[]
		    
			for j in range(len(R16_local_sn)):
				if hosts[i] == R16_local_sn[j][0]:
					temp.append(R16_local_sn[j])
			    
			k = len(temp)
			host = []
			ID = []
			m = np.zeros(k)
			dm = np.zeros(k)
		    
			key = hosts[i]
		    
			for l in range(len(temp)):
				host.append(temp[l][0])
				ID.append(temp[l][1])
				m[l] = temp[l][2]
				dm[l] = temp[l][3]
		
		
			value = Local_SN_data(host,ID,m,dm)
			local_sn_dict[key] = value


		# this block is where the hubble flow sn data will be oragnized 
		#into the hubble flow sn class
		k = len(PS_sn)
		ID = []
		z = np.zeros(k)
		dz = np.zeros(k)
		m = np.zeros(k)
		dm = np.zeros(k)

		for i in range(len(PS_sn)):

			ID.append(PS_sn[i][0])
			z[i] = PS_sn[i][1]
			dz[i] = PS_sn[i][2]
			m[i] = PS_sn[i][3]
			dm[i] = PS_sn[i][4]

		hubble_sn = Hubble_SN_data(ID,z,dz,m,dm)

##############################################################################################
#CALCULATIONS#
##############################################################################################

		# This block is where M_ceph will be calculated from each Anchor

		# period is divided by 10 as does by Esthafio (2020)
		period = np.log10(ceph_dict["N4258"].Period/10)
		dperiod = np.zeros(len(period))
		mh = ceph_dict["N4258"].mh
		dmh = ceph_dict["N4258"].dmh

		anchor_dict["N4258"].Compute_abs_ceph_mag(period,dperiod,mh,dmh)

		# this is the block that calcuates mu to each sn host galaxy

		for key in ceph_dict:
			period = np.log10(ceph_dict[key].Period/10)
			dperiod = np.zeros(len(period))
			mh = ceph_dict[key].mh
			dmh = ceph_dict[key].dmh
			Mceph = anchor_dict["N4258"].Mceph
			dMceph = anchor_dict["N4258"].dMceph

		# This is where the slope of the cephied PL relationship is defined

		slope_array = np.zeros(len(ceph_dict))
		dslope_array = np.zeros(len(ceph_dict))
		w_slope_array = np.zeros(len(ceph_dict))
		w_dslope_array = np.zeros(len(ceph_dict))
		count = 0 
		tot = 0
		# the following 3 lines are parameters for the york fit and may be 
		#removed in future updates
		r = 0
		tol = 10**-15
		n = 20

		for key in ceph_dict:
			x = np.log10(ceph_dict[key].Period/10)
			xerror = np.zeros(len(x))
			y = ceph_dict[key].mh
			yerror = ceph_dict[key].dmh
		    
			[B_0, B_1, sigma_B_0, sigma_B_1, b_save, B_0_simple, B_1_simple] = york_fit(x,y,xerror,yerror,r,tol,n)
		    
		    # this calculates the weighted slope and weighted error of the slope for 
		#each cephied host galaxy
			weight = len(x)
			tot += weight
			w_slope_array[count] = B_1*weight
			w_dslope_array[count] = np.power(sigma_B_1,2)*weight
			count+=1

		# This calculates the overall slope of the PL relationship for cephieds, and its error
		slope = sum(w_slope_array)/tot
		dslope = np.sqrt(sum(w_dslope_array)/tot)/np.sqrt(len(ceph_dict))

		for key in ceph_dict:
			period = np.log10(ceph_dict[key].Period/10)
			dperiod = np.zeros(len(period))
			mh = ceph_dict[key].mh
			dmh = ceph_dict[key].dmh
			Mceph = anchor_dict["N4258"].Mceph
			dMceph = anchor_dict["N4258"].dMceph
		    
			ceph_dict[key].proto_Compute_mu(mh,dmh,period,dperiod,Mceph,dMceph,slope,dslope)

		# This block is where Msn will be calculated from Ceph_SN hosts
		x = []
		y = []
		xerror = []
		yerror = []

		for key in local_sn_dict:
			local_sn_dict[key].mu = ceph_dict[key].mu
			local_sn_dict[key].dmu = ceph_dict[key].dmu

			x.append(local_sn_dict[key].mu)
			y.append(float(local_sn_dict[key].m))
			xerror.append(local_sn_dict[key].dmu)
			yerror.append(float(local_sn_dict[key].dm))

		x = np.array(x)
		y = np.array(y)
		xerror = np.array(xerror)
		yerror = np.array(yerror)

		[Msn, B1, dMsn, sigma_B1] = weighted_fixed_slope(x,y,1,0,xerror,yerror)

		# This block is where DM_sn_obs will be calculated for each SN
		m = hubble_sn.m
		dm = hubble_sn.dm
		hubble_sn.Compute_hubble_mu(m,dm,Msn,dMsn)

		self.hubble_mu = hubble_sn.mu
		self.hubble_dmu = hubble_sn.dmu
		self.hubble_z = hubble_sn.z
		self.hubble_dz = hubble_sn.dz

		print("Abs. Ceph. Mag:", Mceph)
		print("Abs. Ceph. Mag Error:",dMceph)
		print('')
		print("Ceph. P-L Slope:", slope)
		print("Ceph. P-L Slope Error:", dslope)
		print('')
		print("Anchor Msn:",Msn)
		print("Anchor dMsn:",dMsn)
		
	def loglkl(self, cosmo, data):

		z = self.hubble_z
		dz = self.hubble_dz

		k = len(self.hubble_dmu)

		cosmo_mu = np.zeros(k)
		cosmo_dmu = np.zeros(k)

		for i in range(k):

			cosmo_mu[i] = 5*np.log10(cosmo.luminosity_distance(z[i]))+25

		residuals = np.zeros(k)
		residuals = self.hubble_mu - cosmo_mu

		#jac = ((1+z)/cosmo.Hubble(z))+(cosmo.luminosity_distance(z)/(1+z))

		#cov = np.diag(np.sqrt(self.hubble_dmu**2+(jac*dz)**2))
		cov = np.diag(np.sqrt(self.hubble_dmu**2+(dz)**2))

		cov = la.cholesky(cov, lower=True, overwrite_a=True)

		residuals = la.solve_triangular(cov,residuals, lower=True, check_finite=False)
		
		chi2 = (residuals**2).sum()
		

		lkl = -np.log10(0.5*chi2)
		print('This is the distanceladder lkl:',lkl)
	
		return lkl

		

		





