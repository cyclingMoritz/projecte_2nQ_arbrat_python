# -*- coding: utf-8 -*-
"""
Created on Thu Mar 30 11:32:40 2023

@author: Luca Liebscht
"""

#libraries to import
import sys
import math
import processing
import string
from qgis.core import *
from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import QApplication, QWidget, QInputDialog, QLineEdit
from PyQt5.QtGui import QIcon
from qgis.PyQt import QtGui

#Define default values

class processes():  #Class that stores the processes to create the grid and count the number of points in each cell
    #Entered by the user
    layer_name = ''
    width = 0
    height = 0
    #Calculated
    crs = ''
    coordinates = ''
    #qgis
    qgs_layer= None
    grid = None
    count = None
    def __init__(self,layer_name = 'Arbrat', width = 100, height = 100):#We inicialize the class with default values
        self.layer_name=layer_name
        self.width=width
        self.height=height
        
        self.qgs_layer=self.get_layer() #here we get the layer to process
        self.crs=self.get_crs() #Here we get the CRS
        self.coordinates=self.get_extension() #Here we get the extension of the layer
    def get_layer(self):    #This function gets the first layer that has the specified name
        return QgsProject.instance().mapLayersByName(self.layer_name)[0]
    def get_crs(self):  #This function gets the CRS of the specified layer
        return self.qgs_layer.crs() 
    def get_extension(self):    #This function gets the extension (Coordenates) of the layer
        xmin, ymin, xmax, ymax = self.qgs_layer.extent().toRectF().getCoords()#We obtain the extension of the layer 
        xmin = math.floor(xmin) #Round
        ymin = math.floor(ymin) #Round
        xmax = math.ceil(xmax) #Round
        ymax = math.ceil(ymax) #Round
        template = "{},{},{},{}" # Creation of a template to format the coordinates
        return template.format(xmin, xmax, ymin, ymax) #We format the coordinates
    def calculate_cell_dimesions(self,columns,rows):    #This function calculated the cell dimensions based on the numer of columns and rows
        xmin, ymin, xmax, ymax = self.qgs_layer.extent().toRectF().getCoords()#We obtain the extension of the layer 
        self.width = (xmax-xmin)/columns #We calculate the width of the cell 
        self.heigh = (ymax-ymin)/rows #We calculate the heigh of the cell 
    def create_grid(self):  #This function created a a grid
        params = {'TYPE':2, #Parameters
          'EXTENT':self.coordinates,
          'HSPACING':self.height,
          'VSPACING':self.width,
          'HOVERLAY':0,
          'VOVERLAY':0,
          'CRS':self.crs,
          'OUTPUT':'memory:grid'}
        result=processing.run('native:creategrid', params)  #We run the process
        self.grid=result['OUTPUT']  #We store the output
    def count_points(self): #This function counts the number of points in each of the cells of the grid
        params = {#Parameters
            "POLYGONS": self.grid,
            "POINTS": self.layer_name,
            "OUTPUT": "memory:heat_grid" #The text after memory is the name
        }
        result = processing.run("native:countpointsinpolygon", params)  #We run the process
        self.count = result["OUTPUT"]   #We store the output
    def add_layer(self,layer):  #This function adds the layer to the map
        QgsProject().instance().addMapLayer(layer)
        
class color():  #Class that colors the grid based on the number of points
    #Input variables
    layer_name=''
    targetField = ''
    opacity = 0
    intervals = 0
    #Calculated variables
    idx = None
    min_value = 0
    max_value = 0
    #Lists
    intervalsList = []
    rangeList = []
    list_colors = []
    #qgis variables
    qgs_layer= None
    
    def __init__(self,layer_name = 'heat_grid',targetField = 'NUMPOINTS',  opacity = 1, intervals=5):#We inicialize the class with default values
        self.layer_name=layer_name
        self.targetField=targetField
        self.opacity=opacity
        self.intervals=intervals
        
        self.qgs_layer=self.get_layer()
        self.idx=self.get_idx()
        self.min_value,self.max_value=self.get_max_min()
    def get_layer(self):    #This function gets the first layer that has the specified name
        return QgsProject.instance().mapLayersByName(self.layer_name)[0]
    def get_idx(self):  #We get the IDX of the target field
        return self.qgs_layer.fields().indexFromName(self.targetField)#Get IDX
    def get_max_min(self):  #We the the maximim and minimum values
        return self.qgs_layer.minimumValue(self.idx), self.qgs_layer.maximumValue(self.idx)
    def calculate_intervals(self):  #We calculate the intervals based on the amplitude and the number of intervals 
        amplitude=(self.max_value-self.min_value)/self.intervals
        bottom=self.min_value
        for i in range(self.intervals): #We store the intervals
            value= (bottom,bottom+amplitude)
            self.intervalsList.append(value)
            bottom += amplitude
    def generate_color_gradient(self,color1, color2):   #Function that generates the color gradient
        """
        Generates a list of x Hex color codes between color1 and color2
        Made using chat GDP
        """
        if(self.intervals<=2):
            print("The number of intervals is equal or lower than two, no color gradient will be calculated")
        elif(self.intervals>2):
            x=self.intervals-2
            # Check if the input strings are properly formatted Hex color codes
            if not all(c.startswith("#") and len(c) == 7 and all(h in string.hexdigits for h in c[1:]) for c in [color1, color2]):
                raise ValueError("Invalid Hex color code")
    
            # Convert the hex color codes to RGB tuples
            r1, g1, b1 = tuple(int(color1[i:i+2], 16) for i in (1, 3, 5))
            r2, g2, b2 = tuple(int(color2[i:i+2], 16) for i in (1, 3, 5))
    
            # Calculate the step size for each RGB value
            r_step = (r2 - r1) / x
            g_step = (g2 - g1) / x
            b_step = (b2 - b1) / x
    
            # Generate the list of Hex color codes
            colors = []
            for i in range(x+1):
                r = int(round(r1 + (i * r_step)))
                g = int(round(g1 + (i * g_step)))
                b = int(round(b1 + (i * b_step)))
                hex_color = "#{:02x}{:02x}{:02x}".format(r, g, b)
                colors.append(hex_color)
    
            # Add the final color to the list (rounded to nearest integer)
            colors.append(color2)
    
            self.list_colors=colors

    def layer_style(self):  #Function that creates the style of the layer
        amplitude=((self.max_value-self.min_value)/self.intervals)
        bottom=self.min_value
        
        for i in range(self.intervals):
            minVal = bottom
            if(i==self.intervals-1):
                amplitude+=0.1#Sometimes it does not get the max value
            maxVal = bottom+amplitude
            bottom += amplitude
            
            lab = 'Group '+str(i+1) # range label
            rangeColor = QtGui.QColor(self.list_colors[i])# color (yellow)
            
            # create symbol and set properties
            symbol = QgsSymbol.defaultSymbol(self.qgs_layer.geometryType())
            symbol.setColor(rangeColor)
            symbol.setOpacity(self.opacity)
            #create range and append to rangeList
            range_ = QgsRendererRange(minVal, maxVal, symbol, lab)
            self.rangeList.append(range_)

    def render_colors(self):    #Function that renders the colors 
        groupRenderer = QgsGraduatedSymbolRenderer('', self.rangeList)
        groupRenderer.setMode(QgsGraduatedSymbolRenderer.EqualInterval)
        groupRenderer.setClassAttribute(self.targetField)

        # apply renderer to layer
        self.qgs_layer.setRenderer(groupRenderer)

        # add to QGIS interface
        QgsProject.instance().addMapLayer(self.qgs_layer)


class App(QWidget): #Class that contains the input dialogs

    def __init__(self): #Values of the dialog screen
        super().__init__()
        self.title = 'PyQt5 input dialogs - pythonspot.com'
        self.left = 10
        self.top = 10
        self.width = 5000
        self.height = 4000
        self.initUI()
    
    def initUI(self):   
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        
    def select_mode(self):  #Input dialog to select the mode of operation
        items = ("Automatic","Manual")
        item, okPressed = QInputDialog.getItem(self, "Select option","Mode:", items, 0, False)
        if okPressed and item:
            return(item)

    def grid_mode(self):    #Input dialog to select how the grid will be made
        items = ("Set rows and columns","Set width and height")
        item, okPressed = QInputDialog.getItem(self, "Select the way the grid will be made","Options:", items, 0, False)
        if okPressed and item:
            return(item)
        
    def input_int(self, text, category,default):    #Input dialog to add an integrers
        i, okPressed = QInputDialog.getInt(self, text,str(category)+":", default, 1, 300, 1)
        if okPressed:
            return i
    def input_str(self, text,category,default): #Input dialog to add strings
        text, okPressed = QInputDialog.getText(self, text ,category , QLineEdit.Normal, default)
        if okPressed and text != '':
            return text
    def getDouble (self,text,category,default): #Input dialog to get doubles
        d, okPressed = QInputDialog . getDouble (self , text,str(category)+":",  0.5, 0, 1, 3)
        if okPressed :
            return d


class main():   #Main class that clalls the other classes (It could also be a function)
    QgsProject.instance().removeMapLayer("heat_grid") #We remove the grid in case it already existed
    dialog= App()   #We define the app class that allows the use of dialogs
    select_mode=dialog.select_mode()    #We ask the user to select the mode of operation
    if(select_mode=="Automatic"):   #The automatic mode runs everything using default values
        part_one = processes()
        part_one.create_grid()
        part_one.count_points()
        part_one.add_layer(part_one.count)
        
        part_two = color()
        color1 = "#A02B2B"  # Red
        color2 = "#2DA02B"  # Green
    
        part_two.generate_color_gradient(color1,color2)
        part_two.layer_style()
        part_two.render_colors()
    elif(select_mode=="Manual"):    #The manual mode asks the user to define all the values
        #print("Unfortunately, this has not been developed yet")
        layer=dialog.input_str("Type the name of the layer","Layer","Arbrat")   #We ask the name of the layer
        
        grid_mode=dialog.grid_mode()    #We ask how to create the grid
        
        if(grid_mode=="Set width and height"):  #We create the grid with the width and height
            width=dialog.input_int("Type the width","Width",50)
            height=dialog.input_int("Type the height","Height",50)
            part_one = processes(layer,width,height)  
        elif(grid_mode=="Set rows and columns"):    #We create the grid with the rows and columns
            columns=dialog.input_int("Type the numer of columns","Column",50)
            rows=dialog.input_int("Type the number of rows","Row",100)
            part_one = processes(layer) 
            part_one.calculate_cell_dimesions(columns,rows)
        part_one.create_grid()  
        part_one.count_points()
        part_one.add_layer(part_one.count)
          
        layer=dialog.input_str("Type the name of the layer","Layer","heat_grid")
        targetField=dialog.input_str("Type the name of the target field","Target Field","NUMPOINTS")
        opacity=dialog.getDouble("Type the opacity","Opacity",0.5)
        intervals=dialog.input_int("Type the number of intervals","Intervals",9)
        
        part_two = color(layer,targetField,opacity,intervals)
        
        color1=dialog.input_str("Type the hexadecimal value of the color","Color","#A02B2B")
        color2=dialog.input_str("Type the hexadecimal value of the color","Color","#2DA02B")
    
        part_two.generate_color_gradient(color1,color2)
        part_two.layer_style()
        part_two.render_colors()
        
test=main()
