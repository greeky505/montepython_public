
from montepython.likelihood_class import Likelihood

class omega_b(Likelihood):
	def loglkl(self,cosmo,data):
		chi2 =(cosmo.omega_b() - self.BBN)**2/self.dBBN**2

		lkl = -0.5*chi2
		
		print('This is the lkl of omega_b:',lkl)
		
		return lkl
