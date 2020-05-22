import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
from scipy import interpolate
from scipy.signal import savgol_filter
from bokeh.plotting import figure, output_file, show
from bokeh.models import ColumnDataSource, Range1d,Span,Button,TextInput, Legend,Select,CustomJS, Column,Toggle, Div,TextInput,Slider,LinearColorMapper, LogTicker, ColorBar,Range1d
from bokeh.io import push_notebook, show, output_notebook,curdoc
from bokeh.layouts import gridplot,row
from bokeh.palettes import all_palettes,Viridis5,Viridis3
from bokeh import events
from bokeh.client import push_session, pull_session


energies = np.array([80,150,250,400,650])
all_data={}

for value in energies:
    name = 'bokeh-app/pea_'+str(value)+'nj.txt'
    data = pd.read_csv(name)
    data.set_index(['time ps'], inplace=True)
    data.columns = data.columns.values.astype(float)
    data.index.name=None
    all_data[value]=data
    
    
# usefull variable 
y_min = all_data[80].index.min()
y_max = all_data[80].index.max()
new_y =all_data[80].index.values
x_min = all_data[80].columns.min()
x_max = all_data[80].columns.max()
new_x = all_data[80].columns.values
amplitude_min = all_data[650].values.min()
amplitude_max = all_data[650].values.max()
  
# Top figure
p_top = figure(title='decay',x_axis_label='time (ps)',y_axis_label='DA',x_axis_type='log',plot_width=500, plot_height=250,tools="pan,save,wheel_zoom,reset")
p_top.x_range.range_padding = p_top.y_range.range_padding = 0
p_top.y_range = Range1d(amplitude_min,amplitude_max)
p_top.x_range = Range1d(y_min,y_max)
   
source_top = ColumnDataSource(data=dict(x=new_y, y=all_data[650].iloc[:,100]))
top_line = p_top.line('x', 'y',source=source_top,color='red')
hline = Span(location=0, dimension='width', line_color='black', line_width=1)
p_top.renderers.extend([hline])

# central figure
p_center= figure(title='map',x_axis_label='wavelength (nm)',y_axis_label='time (ps)',y_axis_type='log',plot_width=500, plot_height=500,tools="pan,save,wheel_zoom,reset")
p_center.x_range.range_padding = p_center.y_range.range_padding = 0

source_image=ColumnDataSource(data=dict(image=[all_data[650].values]))
p_center.image('image',source=source_image,x=x_min,y=y_min, dh=y_max-y_min, dw=x_max-x_min, palette = "Viridis256", level="image")
p_center.grid.grid_line_width = 0.1
    # color bar
color_mapper = LinearColorMapper(palette="Viridis256", low=amplitude_min, high=amplitude_max)
color_bar = ColorBar(color_mapper=color_mapper,label_standoff=12, border_line_color=None, location=(0,0), orientation="horizontal")

hline_y = Span(location=0, dimension='width', line_color='white', line_width=1,name='span_y')
hline_x = Span(location=0, dimension='height', line_color='white', line_width=1,name='span_x')

p_center.renderers.extend([hline_y,hline_x])
p_center.add_layout(color_bar, 'below')

# righ figure
p_right= figure(title='specra',x_axis_label='nm',y_axis_label='DA',plot_width=500, plot_height=500,margin = (0,0,0,0),tools="pan,save,wheel_zoom,reset")
p_right.x_range.range_padding = p_right.y_range.range_padding = 0

source_right = ColumnDataSource(data=dict(x=new_x, y=all_data[650].iloc[100,:]))
p_right.line('x', 'y',source = source_right,color='red')
p_right.y_range = Range1d(amplitude_min,amplitude_max)
p_right.renderers.extend([hline])

# power dependent nm
#list_nm = [495,510,524]
def p_dep(list_nm=[495,510,524]):
    power_dep = pd.DataFrame(index=energies,columns=list_nm)
    for nm in list_nm:
        max_point=[]
        for data in all_data:
            max_point.append(all_data[data].iloc[np.searchsorted(new_y, 0.4, side='right'),
                                                 np.searchsorted(new_x, nm, side='right')])
        power_dep[nm]=max_point
        power_dep.columns=power_dep.columns.astype(str)
    return power_dep

power_dep=p_dep()
#power_dep.columns=power_dep.columns.astype(str)
source_power = ColumnDataSource(power_dep)

p_power = figure(title='power dependence',x_axis_label='excitation energy (nj)',y_axis_label='DA',plot_width=500, plot_height=500,tools="pan,save,wheel_zoom,reset")
p_power.renderers.extend([hline])
for value in power_dep.columns.astype(str):
    p_power.line(x='index',y=value,source=source_power)

# slider and buttons

nm = Slider(title="nm", value=x_min, start=int(x_min), end=int(x_max), step=1,width = 445,margin = (0,0,0,60))
time = Slider(title="time 10^", value=np.log10(y_min), 
              start=np.log10(y_min), end=np.log10(y_max), 
              step=0.01,height = 380,margin = (10,0,0,0),orientation='vertical',direction='rtl')
#

selected_nm=TextInput(value='495,510,524',title='selected nm')
show_all_power = Toggle(label='show all power')

nm_int=np.array(str.split(selected_nm.value,',')).astype(int)

def legend_plot(fig,label):
    legend_label=[]
    for r,label in zip(fig.renderers[1:],label):
        legend_label.append((label+'nm',[r]))
    return legend_label

legend = Legend(items=legend_plot(p_power,nm_int.astype(str)))
#p_power.add_layout(legend, 'right')

energies_str=energies.astype(str).tolist()
power_choice = Select(title="excitation power :", value=energies_str[0],options=energies_str)
plot_power=Button(label='plot power dep')

widget = Column(power_choice,show_all_power,selected_nm,plot_power)

# callback function for interactivity

def callback_nm(attr, old, new):
    source_top.data = dict(x=new_y, 
                           y=all_data[int(power_choice.value)].iloc[:,np.searchsorted(new_x, nm.value, side='right')])
    p_top.title.text = str(round(nm.value,0))
    p_center.select(name='span_x').location=nm.value

def callback_time(attr, old, new):
    source_right.data = dict(x=new_x, y=all_data[int(power_choice.value)].iloc[np.searchsorted(new_y, 10**time.value, side='right'),:])
    p_right.title.text = str(round(time.value,0))
    p_center.select(name='span_y').location=10**time.value

def callback(event):
    p_center.title.text = str(round(event.x,2))+'-'+str(round(event.y,2))
    nm.value=event.x
    time.value=np.log10(event.y)
    p_center.select(name='span_x').location=event.x
    p_center.select(name='span_y').location=event.y
    
    
def callback_power(attr, old, new):
    amplitude_min = all_data[int(power_choice.value)].values.min()
    amplitude_max = all_data[int(power_choice.value)].values.max()
    source_image.data=dict(image=[all_data[int(power_choice.value)].values])
    #p_center.image(image=[all_data[int(power_choice.value)].values],x=x_min,y=y_min, dh=y_max-y_min, dw=x_max-x_min, palette = "Viridis256", level="image")
    p_right.y_range.end = p_top.y_range.end = amplitude_max
    p_right.y_range.start = p_top.y_range.start = amplitude_min
    
def callback_all_power(event):
    #p_top.title.text = str(show_all_power.active)
    if show_all_power.active:
        p_top.title.text = str(show_all_power.active)
        for value,color in zip(energies,Viridis5):
            source_top_all = ColumnDataSource(dict(x=new_y, 
                           y=all_data[value].iloc[:,np.searchsorted(new_x, nm.value, side='right')]))
            p_top.line('x', 'y',source=source_top_all,color=color)
            
            source_right_all = ColumnDataSource(data= dict(x=new_x, y=all_data[value].iloc[np.searchsorted(new_y, 10**time.value, side='right'),:]))
            p_right.line('x', 'y',source = source_right_all,color=color)
        
        p_top.y_range.end=p_right.y_range.end = all_data[energies.max()].values.max()
        
    else:
        p_top.renderers=[p_top.renderers[0],p_top.renderers[1]]
        p_right.renderers=[p_right.renderers[0],p_right.renderers[1]]
        p_top.y_range.end =p_right.y_range.end= all_data[int(power_choice.value)].values.max()

def callback_plot(event):
    if p_power.right != []:
        p_power.right=[]
        
    nm_int=np.array(str.split(selected_nm.value,',')).astype(int)
    power_dep=p_dep(nm_int)   
    source_power = {'index': power_dep.index.astype(int).to_list()}
    source_power.update(power_dep.to_dict(orient='list'))
    
    p_power.renderers=[p_power.renderers[0]]
    for value,color in zip(power_dep.columns.astype(str),Viridis3):
        p_power.line(x='index',y=value,source=source_power,color=color)
    
    legend = Legend(items=legend_plot(p_power,nm_int.astype(str)))
    #p_power.add_layout(legend, 'right')
    
    
    

# event activation
nm.on_change('value', callback_nm) 
time.on_change('value', callback_time) 
p_center.on_event(events.Tap,callback)
power_choice.on_change('value',callback_power,callback_nm,callback_time)
show_all_power.on_click(callback_all_power)
plot_power.on_click(callback_plot)


# layout config
layout = gridplot([[p_top,None,widget],[nm],[p_center,time,p_right],[p_power]])
curdoc().add_root(layout)