import scipy.optimize as sp
import numpy as np
import qexpy.error as qe
import qexpy.utils as qu
import qexpy.fitting as qf
import qexpy.plot_utils as qpu

from math import pi
import bokeh.plotting as bp
import bokeh.io as bi
import bokeh.models as mo
import bokeh.palettes as bpal

from ipywidgets import interact 

CONSTANT = qu.number_types
ARRAY = qu.array_types


class Plot:
    '''Object for plotting and fitting datasets built on
    Measurement_Arrays

    The Plot object holds a list of XYDatasets, themselves containing
    pairs of MeasurementArrays holding x and y values to be plotted and 
    fitted. The Plot object uses bokeh to display the data, along with
    fit functions, and user-specified functions. One should configure
    the various aspects of the plot, and then call the show() function
    which will actually build the bokeh object and display it. 
    '''

    def __init__(self, x=None, y=None, xerr=None, yerr=None, data_name=None, dataset=None):
        '''
        Constructor requiring x and y data or a XYDataset

        Plotting objects do not create Bokeh objects until shown or if the
        Bokeh object is otherwise requested. Class methods built here are
        used to record the data to be plotted and track what the user has
        requested to be plotted.
        '''
    
        #Colors to be used for coloring elements automatically
        self.color_palette = bpal.Set1_9
        self.color_count = 0
    
        #The data to be plotted are held in a list of datasets:
        self.datasets=[]
        if dataset != None:
            self.datasets.append(dataset)
        else:
            self.datasets.append(qf.XYDataSet(x, y, xerr=xerr, yerr=yerr, data_name=data_name))
        
        #Each data set has a color, so that the user can choose specific
        #colors for each dataset
        self.datasets_colors=[]
        self.datasets_colors.append(self._get_color_from_palette())
            
        self.xunits = self.datasets[-1].xunits
        self.xname = self.datasets[-1].xname
        
        self.yunits = self.datasets[-1].yunits
        self.yname = self.datasets[-1].yname    
        
        self.errorband_sigma = 1.0
        self.show_residuals=False
        
        #Add margins to the range of the plot
        self.x_range_margin = 0.5
        self.y_range_margin = 0.5
        
        #Get the range from the dataset (will include the margin)
        self.set_range_from_dataset(self.datasets[-1])
        
        #Dimensions of the figure
        self.dimensions = [600, 400]
        
        #Functions that the user can add to be plotted
        self.user_functions_count=0
        self.user_functions = []
        self.user_functions_pars = []
        self.user_functions_names = []
        self.user_functions_colors = []
        
        #Some parameters to make the plots have proper labels
        self.axes = {'xscale': 'linear', 'yscale': 'linear'}
        self.legend_location = "top_left"
        self.labels = {
            'title': self.datasets[-1].name,
            'xtitle': self.xname+' ['+self.xunits+']',
            'ytitle': self.yname+' ['+self.yunits+']',
            'data': data_name }
                      
        self.plot_para = {
            'filename': 'Plot'}
        
    def _get_color_from_palette(self):
        '''Automatically select a color from the palette'''
        self.color_count += 1
        return self.color_palette[self.color_count-1]
    
    def fit(self, model=None, parguess=None, fit_range=None, datasetindex=-1):
        '''Fit a dataset to model - calls XYDataset.fit and returns a 
        Measurement_Array of fitted parameters'''
        return self.datasets[datasetindex].fit(model, parguess, fit_range)
        
    def print_fit_parameters(self, dataset=-1):
        if self.datasets[-1].nfits>0:
            print("Fit parameters:\n"+str(self.datasets[dataset].fit_pars[-1]))    
        else:
            print("Datasets have not been fit")
            
###############################################################################
# User Methods for adding to Plot Objects
###############################################################################

    def add_residuals(self):
        '''Add a subfigure with residuals to the main figure when plotting'''
        if self.datasets[-1].nfits>0:
            self.show_residuals = True

    
    def add_function(self, function, pars = None, name=None, color=None):
        '''Add a user-specifed function to the list of functions to be plotted.
        
        All datasets are functions when populate_bokeh_figure is called
        - usually when show() is called
        '''
        
        xvals = np.linspace(self.x_range[0],self.x_range[1], 100)
        
        #check if we should change the y-axis range to accomodate the function
        if not isinstance(pars, np.ndarray) and pars == None:
            fvals = function(xvals)
        elif isinstance(pars, qe.Measurement_Array) :
            recall = qe.Measurement.minmax_n
            qe.Measurement.minmax_n=1
            fmes = function(xvals, *(pars))
            fvals = fmes.get_means()
            qe.Measurement.minmax_n=recall
        elif isinstance(pars,(list, np.ndarray)):
            fvals = function(xvals, *pars)
        else:
            print("Error: Not a recognized format for parameter")
            return
                 
        fmax = fvals.max()+self.y_range_margin
        fmin = fvals.min()-self.y_range_margin
        
        if fmax > self.y_range[1]:
            self.y_range[1]=fmax
        if fmin < self.y_range[0]:
            self.y_range[0]=fmin
            
        self.user_functions.append(function)
        self.user_functions_pars.append(pars)
        fname = "userf_{}".format(self.user_functions_count) if name==None else name
        self.user_functions_names.append(fname)
        self.user_functions_count +=1
        
        if color is None:
            self.user_functions_colors.append(self._get_color_from_palette())
        else: 
            self.user_functions_colors.append(color)
        
    def add_dataset(self, dataset, color=None, name = None):
        '''Add a dataset to the Plot object. All datasets are plotted
        when populate_bokeh_figure is called - usually when show() is called'''
        self.datasets.append(dataset)
        if color is None:
            self.datasets_colors.append(self._get_color_from_palette())
        else: 
            self.datasets_colors.append(color)
        if name != None:
            self.datasets[-1].name=name
            
        x_range = dataset.get_x_range(self.x_range_margin)
        y_range = dataset.get_y_range(self.y_range_margin)
        
        if x_range[0] < self.x_range[0]:
            self.x_range[0]=x_range[0]
        if x_range[1] > self.x_range[1]:
            self.x_range[1]=x_range[1]
            
        if y_range[0] < self.y_range[0]:
            self.y_range[0]=y_range[0]
        if y_range[1] > self.y_range[1]:
            self.y_range[1]=y_range[1] 
 

#
###############################################################################
# Methods for changing parameters of Plot Object
###############################################################################
    def set_range_from_dataset(self, dataset):
        '''Use a dataset to set the range for the figure'''
        self.x_range = dataset.get_x_range(self.x_range_margin)
        self.y_range = dataset.get_y_range(self.y_range_margin)
        
    def set_plot_range(self, x_range=None, y_range=None):
        '''Set the range for the figure'''
        if type(x_range) in ARRAY and len(x_range) is 2:
            self.x_range = x_range
        elif x_range is not None:
            print('''X range must be a list containing a minimun and maximum
            value for the range of the plot.''')

        if type(y_range) in ARRAY and len(y_range) is 2:
            self.y_range = y_range
        elif y_range is not None:
            print('''Y range must be a list containing a minimun and maximum
            value for the range of the plot.''')

            
    def set_labels(self, title=None, xtitle=None, ytitle=None, data_name=None ):
        '''Change the labels for plot axis, datasets, or the plot itself.

        Method simply overwrites the automatically generated names used in
        the Bokeh plot.'''
        if title is not None:
            self.labels['title'] = title

        if xtitle is not None:
            self.labels['xtitle'] = xtitle

        if ytitle is not None:
            self.labels['ytitle'] = ytitle

        if data_name is not None:
            self.labels['Data'] = data_name

    def resize_plot(self, width=None, height=None):
        if width is None:
            width = 600
        if height is None:
            height = 400
        self.dimensions = [width, height]

    def set_errorband_sigma(self, sigma=1):
        '''Change the confidence bounds of the error range on a fit.
        '''
        self.errorband_sigma = sigma

###############################################################################
# Methods for Returning or Rendering Bokeh
###############################################################################
            
    def show(self, output='inline', populate_figure=True):
        '''
        Show the figure, will call populate_bokeh_figure by default to
        add all the items (datasets, fit functions, user-specified functions)
        to the plot
        '''
        
        self.set_bokeh_output(output)
        
        if populate_figure:
            bp.show(self.populate_bokeh_figure())
        else:
            bp.show(self.bkfigure)
    
    def set_bokeh_output(self, output='inline'):
        '''Choose where to output (in a notebook or to a file)'''
        
        if output == 'file' or not qu.in_notebook():
            bi.output_file(self.plot_para['filename']+'.html',
                           title=self.attributes['title'])
        elif not qu.bokeh_ouput_notebook_called:
            bi.output_notebook()
            # This must be the first time calling output_notebook,
            # keep track that it's been called:
            qu.bokeh_ouput_notebook_called = True
        else:
            pass
            
    def populate_bokeh_figure(self):  
        '''Main method for building the plot - this creates the Bokeh figure,
        and then loops through all datasets (and their fit functions), as
        well as user-specified functions, and adds them to the bokeh figure'''
        
        # create a new bokeh figure
        self.bkfigure = self.initialize_bokeh_figure(residuals=False)
        
        # create the one for residuals if needed
        if self.show_residuals:
            self.bkres = self.initialize_bokeh_figure(residuals=True)
                              
        #plot the datasets and their latest fit
        count = 0
        for dataset in self.datasets:
            color = self.datasets_colors[count]
            qpu.plot_dataset(self.bkfigure, dataset, residual=False,
                            data_color=color)
                   
            if dataset.nfits>0:
                qpu.plot_function(self.bkfigure, function=dataset.fit_function[-1],
                                  xdata=dataset.xdata,pars=dataset.fit_pars[-1],
                                  n=100, legend_name=dataset.fit_function_name[-1],
                                  color=color, errorbandfactor=self.errorband_sigma)
                
                #Draw fit parameters only for the first dataset
                if count<1:
                     for i in range(dataset.fit_npars[-1]):
                        #shorten the name of the fit parameters
                        short_name =  dataset.fit_pars[-1][i].__str__().split('_')
                        short_name = short_name[0]+"_"+short_name[-1]
                        citation = mo.Label(x=590, y=320+20*i,
                                            text_align='right',
                                            text_baseline='top',
                                            text_font_size='11pt',
                                            x_units='screen',
                                            y_units='screen',
                                            text=short_name,
                                            render_mode='css',
                                            background_fill_color='white',
                                            background_fill_alpha=1.0)
                        self.bkfigure.add_layout(citation)
                        
                if self.show_residuals:
                    qpu.plot_dataset(self.bkres, dataset, residual=True,
                                     data_color=color)
            count += 1

        #Now add any user defined functions:
        xvals = [self.x_range[0]+self.x_range_margin, 
                 self.x_range[1]-self.x_range_margin]
   
        count = 0
        for func, pars, fname in zip(self.user_functions,self.user_functions_pars,self.user_functions_names):
            color = self.user_functions_colors[count]
            qpu.plot_function(self.bkfigure, function=func, xdata=xvals,
                              pars=pars, n=100, legend_name= fname,
                              color=color, errorbandfactor=self.errorband_sigma)
            count += 1
        
        #Specify the location of the legend
        self.bkfigure.legend.location = self.legend_location
        
        if self.show_residuals:
            self.bkfigure = bi.gridplot([[self.bkfigure], [self.bkres]])
            
        return self.bkfigure
    
    def initialize_bokeh_figure(self, residuals=False):  
        '''Create the bokeh figure with desired labeling and axes'''
        if residuals==False:
            return bp.figure(
                tools='save, pan, box_zoom, wheel_zoom, reset',
                width=self.dimensions[0], height=self.dimensions[1],
                y_axis_type=self.axes['yscale'],
                y_range=self.y_range,
                x_axis_type=self.axes['xscale'],
                x_range=self.x_range,
                title=self.labels['title'],
                x_axis_label=self.labels['xtitle'],
                y_axis_label=self.labels['ytitle'],
            )
        else:
            return bp.figure(
                width=self.dimensions[0], height=self.dimensions[1]//3,
                tools='save, pan, box_zoom, wheel_zoom, reset',
                y_axis_type='linear',
                y_range=self.datasets[-1].get_yres_range(),
                x_range=self.bkfigure.x_range,
                x_axis_label=self.labels['xtitle'],
                y_axis_label='Residuals'
            )
       
        
    def show_linear_fit(self, output='inline'):
        '''Fits the last dataset to a linear function and displays the
        result. The fit parameters are not displayed as this function is 
        designed to be used in conjunction with interarct_linear_fit()'''
        
        
        if len(self.datasets) >1:
            print("Warning: only using the last added dataset, and clearing previous fits")
                     
        dataset = self.datasets[-1]
        color = self.datasets_colors[-1]
        
        dataset.clear_fits()
        dataset.fit("linear")
        
        func = dataset.fit_function[-1]
        pars = dataset.fit_pars[-1]
        fname = "linear"       
        
        #Extend the x range to 0
        if self.x_range[0] > -0.5:
            self.x_range[0] = -0.5
            self.y_range[0] = dataset.fit_function[-1](self.x_range[0], *pars.get_means())
        
        self.bkfigure = self.initialize_bokeh_figure(residuals=False)
        
        qpu.plot_dataset(self.bkfigure, dataset, residual=False,
                         data_color=color)
        
        xvals = [self.x_range[0]+self.x_range_margin, 
                 self.x_range[1]-self.x_range_margin]
        
        line, patches = qpu.plot_function(self.bkfigure, function=func, xdata=xvals,
                              pars=pars, n=100, legend_name= fname,
                              color=color, errorbandfactor=self.errorband_sigma)
        
        #stuff that is only needed by interact_linear_fit
        self.linear_fit_line = line
        self.linear_fit_patches = patches
        self.linear_fit_pars = pars
               
        #Specify the location of the legend
        self.bkfigure.legend.location = self.legend_location      
        self.show(output=output,populate_figure=False)
        
        error_range=2

    def interact_linear_fit(self, error_range = 2):  
        '''After show_linear_fit() has been called, this will display
        sliders allowing the user to adjust the parameters of the linear
        fit - only works in a notebook, require ipywigets''' 
        
        off_mean = self.linear_fit_pars[0].mean
        off_std = self.linear_fit_pars[0].std
        off_min = off_mean-error_range*off_std
        off_max = off_mean+error_range*off_std
        off_step = (off_max-off_min)/50.
       
        slope_mean = self.linear_fit_pars[1].mean
        slope_std = self.linear_fit_pars[1].std
        slope_min = slope_mean-error_range*slope_std
        slope_max = slope_mean+error_range*slope_std
        slope_step = (slope_max-slope_min)/50.
        
            
        @interact(offset=(off_min, off_max, off_step),
                  slope=(slope_min, slope_max, slope_step),
                  offset_err = (0, 2.*off_std, off_std/50.),
                  slope_err = (0, 2.*slope_std, off_std/50.),
                  correlation = (-1,1,0.05)                 
                 )
        def update(offset=off_mean, slope=slope_mean, offset_err=off_std, slope_err=slope_std, correlation=0.1):
            
           
            
            recall = qe.Measurement.minmax_n
            qe.Measurement.minmax_n=1
            omes = qe.Measurement(offset,offset_err)
            smes = qe.Measurement(slope,slope_err)
            omes.set_correlation(smes,correlation)
            xdata = np.array(self.linear_fit_line.data_source.data['x'])
            fmes = omes+ smes*xdata
            qe.Measurement.minmax_n=recall
            
            ymax = fmes.get_means()+fmes.get_stds()
            ymin = fmes.get_means()-fmes.get_stds()        
            
            self.linear_fit_line.data_source.data['y'] = fmes.get_means()
            self.linear_fit_patches.data_source.data['y'] = np.append(ymax,ymin[::-1])

            bi.push_notebook()

            
        