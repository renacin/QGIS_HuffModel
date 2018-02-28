
"""
***************************************************************************
    RyersonUniversity_HuffModel.py
    ---------------------
    Date                   : 01/01/2018
    Creator(s)             : Renacin Matadeen, Micheal Morris
    Email                  : Ren @ renacin.matadeen@ryerson.ca
***************************************************************************
*                                                                                                                                      * 
*                                                                                                                                      * 
*                               ADD PURPOSE & COPYRIGHT INFORMATION                                                                    * 
*                                                                                                                                      * 
*                                                                                                                                      * 
***************************************************************************
"""


##RyersonUniversityTools=group
##Huff Model=name

##Centroids_Calculated_From=vector
##Unique_Geography_ID_Field=field Centroids_Calculated_From

##Point_Observation_File=vector
##Point_Observation_ID_Field=field Point_Observation_File

##Attractiveness_Field=field Point_Observation_File               
##Huff_Exponent_Value=selection 0.5; 1.0; 1.5; 2.0; 2.5; 3.0

##Output_Layer=output file


# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
import os

# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


# Get Layer
lyr_for_centroid_calc = processing.getObject(Centroids_Calculated_From)


# Getting The User Defined Path & Filename
user_directory = Output_Layer
last_occurance = user_directory.rfind("/")
filename_number = last_occurance + 1
dir_path = user_directory[:last_occurance]
path = (user_directory[:last_occurance] + "/")
user_filename = user_directory[filename_number:]


# Make Centroid Layer
lyr_centroid = processing.runalg('qgis:polygoncentroids', lyr_for_centroid_calc, path +"Centroids_" + user_filename)


# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


# Get The CRS Of The First Layer, Hopefully The Polygon Layer
layer = iface.activeLayer()
FirstLyrCRS = layer.crs().authid() 
SplitLyrCRS = FirstLyrCRS.split(":")
lyrCRS = SplitLyrCRS[1]


# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


# Euclidean Distance, Huff Probability, and Trade Area Dump File Creation


# Create A Duplicate Of The Census Polygon, For The Euclidean Data Dump
feats = [feat for feat in lyr_for_centroid_calc.getFeatures()]
mem_layer = QgsVectorLayer("Polygon?crs=epsg:" + lyrCRS, "duplicated_layer", "memory")

mem_layer_data = mem_layer.dataProvider()
attr = lyr_for_centroid_calc.dataProvider().fields().toList()
mem_layer_data.addAttributes(attr)
mem_layer.updateFields()
mem_layer_data.addFeatures(feats)
mem_layer.updateExtents()

# Get The Fields In The Duplicated File
layer_dataProvider=mem_layer.dataProvider()
layer_attrib_names = layer_dataProvider.fields()
attributeList = layer_attrib_names.toList()

# Create A List Of Fields To Remove
field_list = []
for attrib in attributeList:
    ps_name = attrib.name()
    field_list.append(ps_name)

index_of_ID = field_list.index(Unique_Geography_ID_Field)
file_range = len(field_list)
index_list = list(range(0, file_range))
index_list.remove(index_of_ID)

mem_layer.dataProvider().deleteAttributes(index_list)
mem_layer.updateFields()

# Save Memory Layer As Pertinent Shapefiles
writer_1 = QgsVectorFileWriter.writeAsVectorFormat(mem_layer, path + "EuclideanDistance_DumpLyr_" + user_filename + ".shp", "UTF-8", None , "ESRI Shapefile")

writer_2 = QgsVectorFileWriter.writeAsVectorFormat(mem_layer, path + "HuffModel_" + user_filename + ".shp", "UTF-8", None , "ESRI Shapefile")

writer_3 = QgsVectorFileWriter.writeAsVectorFormat(mem_layer, path + "HuffModel_TAD_" + user_filename + ".shp", "UTF-8", None , "ESRI Shapefile")


# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


# Calculate Euclidean Distance

# Get the layers.
lyrConsumer = QgsVectorLayer(path +"Centroids_" + user_filename + ".shp", "Centroid", "ogr")
lyrCentre = processing.getObject(Point_Observation_File)

# Get the fields.
fldConsumerID_index = lyrConsumer.fieldNameIndex(Unique_Geography_ID_Field)
fldCentreID_index = lyrCentre.fieldNameIndex(Point_Observation_ID_Field)

# Need to prepare output layer and add new fields.
# New fields are simply the ID of the Centre.
# Loop through each Centre to construct new field names.

lyrOutput = QgsVectorLayer(path + "EuclideanDistance_DumpLyr_" + user_filename + ".shp", "EuclideanDistance_Matrix", "ogr")
provider = lyrOutput.dataProvider() 

# Optimize feature request for this loop.
request1 = QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry).setSubsetOfAttributes([Point_Observation_ID_Field], lyrCentre.fields() )

# The loop.
for centreFeature in lyrCentre.getFeatures(request1):
    
    # Capture value of fldCentreID_index (current ID).
    currentCentreID = centreFeature[fldCentreID_index]

    # Add and name the field. Double type for distances.   
    new_field_name = currentCentreID    
    provider.addAttributes([QgsField(new_field_name, QVariant.Double)])
    lyrOutput.updateFields()

# Set the output layer for editing.
lyrOutput.startEditing()

# Optimize feature request for outer nested loop.
request2 = QgsFeatureRequest().setSubsetOfAttributes([Unique_Geography_ID_Field], lyrConsumer.fields() )
   
# Loop through each Consumer feature.
for consumerFeature in lyrConsumer.getFeatures(request2):
    
    # Capture value of fldConsumerID_index (current ID).
    currentConsumerID = consumerFeature[fldConsumerID_index]
    
    # Loop through each Centre feature.
    for centreFeature in lyrCentre.getFeatures():
        
        # Capture value of fldCentreID_index (current ID).
        currentCentreID = centreFeature[fldCentreID_index]

        # Create a measurement object.
        mObject = QgsDistanceArea()
        
        # Measure the euclidean distance.
        eDistance = mObject.measureLine(consumerFeature.geometry().asPoint(), centreFeature.geometry().asPoint())

        # Set the euclidean distance value of the new Centre field for 
        # the current Consumer and Centre.
        current_distmatrix_field = currentCentreID
        distmatrix_field_index = lyrOutput.fieldNameIndex(current_distmatrix_field)
        lyrOutput.changeAttributeValue(consumerFeature.id(), distmatrix_field_index,eDistance)

# Commit the changes to the layer.
lyrOutput.commitChanges()


# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


# Calculate Huff Probabilities

# Get the layers.
lyrConsumer = QgsVectorLayer(path + "EuclideanDistance_DumpLyr_" + user_filename + ".shp", "EuclideanDistance_Matrix", "ogr")
lyrCentre = processing.getObject(Point_Observation_File)

# Get the fields.
fldCentreAttract_index = lyrCentre.fieldNameIndex(Attractiveness_Field)

# Use dropdown list index to specify the Huff model exponent.
if Huff_Exponent_Value == 0:
    expHuff = 0.5
elif Huff_Exponent_Value == 1:
    expHuff = 1.0
elif Huff_Exponent_Value == 2:
    expHuff = 1.5
elif Huff_Exponent_Value == 3:
    expHuff = 2.0
elif Huff_Exponent_Value == 4:
    expHuff = 2.5
elif Huff_Exponent_Value == 5:
    expHuff = 3.0
    

# Need to prepare output layer and add new field.
# New field is "HP" plus the ID of the Centre.
# Loop through each Centre to construct new field names.
lyrOutput = QgsVectorLayer(path + "HuffModel_" + user_filename + ".shp", "HuffProbability_Values", "ogr")
provider = lyrOutput.dataProvider() 


for centreFeature in lyrCentre.getFeatures():
    
    # Capture value of fldCentreID_index (current ID).
    currentCentreID = centreFeature[fldCentreID_index]

    # Add and name the field.   
    new_field_name = 'HP' + currentCentreID    
    provider.addAttributes([QgsField(new_field_name, QVariant.Double)])
    lyrOutput.updateFields()

# Set the output layer for editing.
lyrOutput.startEditing()


# Loop through each Consumer feature.
for consumerFeature in lyrConsumer.getFeatures():
    
    # Capture value of fldConsumerID_index (current ID).
    currentConsumerID = consumerFeature[fldConsumerID_index]
    
    # Create a total variable for the sumJ of Sj/dij values for use in the nested loop.
    sumJ_sjdivdij = 0.0
    
    # Huff Formula: [(sj/(dij)^b)/(SUMj(sj/(dij)^b))] for a given consumer i and centre j.
    # sumJ_sjdivdij is the denominator of this formula and is first loop below.
    # Exponent b is for friction of distance of the product or service.
    # Second loop below calculates numerator and completes Huff calc for a given ij.
    
    # Loop through each Centre feature to calculate a consumer's sumJ_sjdivdij.
    # This is the Huff formula denominator.
    for centreFeature in lyrCentre.getFeatures():
        
        # Capture value of fldCentreID_index (current ID).
        currentCentreID = centreFeature[fldCentreID_index]
        
        # Capture value of fldCentreAttract_index (current Centre Attractiveness).
        currentCentreAttract = centreFeature[fldCentreAttract_index]
        
        # Capture distance value for this Centre and this Consumer.
        # currentCentreID should match to field name in attrib table.
        currentDistance = consumerFeature[currentCentreID]
        
        # Calculate Centre Attractiveness / Distance^b >> (Sj/dij**b)
        
        # If statement to manage computing cost of exponent calculation.
        if expHuff == 1:
            sjdivdij = currentCentreAttract / currentDistance
        else:
            sjdivdij = currentCentreAttract / (currentDistance**expHuff)
        
        # Add new Sj/dij^b to sumJ_sjdivdij.
        sumJ_sjdivdij = sumJ_sjdivdij + sjdivdij
        
    # Loop through each Centre a second time to calculate Huff proportion.
    for centreFeature in lyrCentre.getFeatures():
        
        # Capture value of fldCentreID_index (current ID).
        currentCentreID = centreFeature[fldCentreID_index]
        
        # Capture value of fldCentreAttract_index (current Centre Attractiveness).
        currentCentreAttract = centreFeature[fldCentreAttract_index]
        
        # Capture distance value for this Centre and this Consumer.
        # currentCentreID should match to field name in attrib table.
        currentDistance = consumerFeature[currentCentreID]
        
        # Calculate Centre Attractiveness / Distance^b >> (Sj/dij**b)
        
        # If statement to manage computing cost of exponent calculation.
        if expHuff == 1:
            sjdivdij = currentCentreAttract / currentDistance
        else:
            sjdivdij = currentCentreAttract / (currentDistance**expHuff)
        
        # Complete the Huff formula calculation.
        calcHuffI = sjdivdij / sumJ_sjdivdij

        # Set the value of the new Hi field for the current Consumer and Centre.
        current_Huff_field = 'HP' + currentCentreID
        Huff_field_index = lyrOutput.fieldNameIndex(current_Huff_field)
        lyrOutput.changeAttributeValue(consumerFeature.id(), Huff_field_index,calcHuffI)

# Commit the changes to the layer.
lyrOutput.commitChanges()


# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


# Calculate Huff Trade Area Designation

# Get the layers.
lyrValues = QgsVectorLayer(path + "HuffModel_" + user_filename + ".shp", "HuffProb", "ogr")
lyrCentre = processing.getObject(Point_Observation_File)

# Need to prepare output layer and add new field.
# New field is "TA" plus the ID of the Centre.
# Loop through each Centre to construct new field names.
lyrOutput = QgsVectorLayer(path + "HuffModel_TAD_" + user_filename + ".shp", "HuffTradeAreaDesignation", "ogr")
provider = lyrOutput.dataProvider() 

for centreFeature in lyrCentre.getFeatures():
    
    # Capture value of fldCentreID_index (current ID).
    currentCentreID = centreFeature[fldCentreID_index]

    # Add and name the field.   
    new_field_name = 'TA' + currentCentreID    
    provider.addAttributes([QgsField(new_field_name, QVariant.Double)])
    lyrOutput.updateFields()


# Set the output layer for editing.
lyrOutput.startEditing()



# Loop through each field in the HuffProb file.
for consumerFeatures in lyrValues.getFeatures():
    # Capture value of fldConsumerID_index (current ID).
    # Remember fldConsumerID_index = lyrConsumer.fieldNameIndex(Unique_Geography_ID_Field)
    currentConsumerID = consumerFeatures[fldConsumerID_index]
    
    
    for centreFeature in lyrCentre.getFeatures():
        
        #Why Did I Add This Pass?
        pass
        
        # Capture value of fldCentreID_index (current ID).
        currentCentreID = centreFeature[fldCentreID_index]
        current_Value = consumerFeatures['HP' + currentCentreID]
        
        
        
        # Set Primary Trade Area
        if (current_Value >= 0.60):
            TradeAreaDesignation = 1
        
        # Set Secondary Trade Area
        elif (0.40 < current_Value < 0.60 ):
            TradeAreaDesignation = 2
            
        # Set Other Trade Area
        else:
            TradeAreaDesignation = 3
            

        current_Huff_field = 'TA' + currentCentreID
        TA_field_index = lyrOutput.fieldNameIndex(current_Huff_field)
        lyrOutput.changeAttributeValue(consumerFeatures.id(), TA_field_index, TradeAreaDesignation)
        
        
# Commit the changes to the layer.
lyrOutput.commitChanges()


# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


#Create a group to hold the Huff Model Main Outputs.
root = QgsProject.instance().layerTreeRoot()
HuffModelGroup = root.addGroup("Huff Model")

#Create a group to hold the Huff Model Main Outputs.
HuffModel_Mapping_Group = root.addGroup("Trade Areas")


# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


# Load Huff Probability Layer To Interface.
HuffModel_Probabilities = QgsVectorLayer(path + "HuffModel_" + user_filename + ".shp", "Huff Model Probabilities", "ogr")
QgsMapLayerRegistry.instance().addMapLayer(HuffModel_Probabilities, False)
HuffModelGroup.insertChildNode(1,QgsLayerTreeLayer(HuffModel_Probabilities))

  
# Load Huff Trade Areas Layer To Interface.
HuffModel_TradeAreas = QgsVectorLayer(path + "HuffModel_TAD_"+ user_filename + ".shp", "Huff Model Trade Areas", "ogr")
QgsMapLayerRegistry.instance().addMapLayer(HuffModel_TradeAreas, False)
HuffModelGroup.insertChildNode(1,QgsLayerTreeLayer(HuffModel_TradeAreas))


# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


#Create A Maps of The All Primary And Secondary Areas

#A Loop That Creates A Copy Of The TradeArea Shapefile For Each Centre, Name By IDs
for centreFeature in lyrCentre.getFeatures():
        
        # Get The ID of the Field
        currentCentreID = centreFeature[fldCentreID_index]
        current_ID = currentCentreID
        
        # Load Huff Trade Areas Layer To Interface.
        HuffModel_TradeAreas = QgsVectorLayer(path + "HuffModel_TAD_"+ user_filename + ".shp", current_ID, "ogr")
        QgsMapLayerRegistry.instance().addMapLayer(HuffModel_TradeAreas, False)
        HuffModel_Mapping_Group.insertChildNode(1,QgsLayerTreeLayer(HuffModel_TradeAreas))
        
        # Create A Thematic Map.
        name = current_ID
        layer = QgsMapLayerRegistry.instance().mapLayersByName( name )[0]


        # get unique values for 'severity' field
        fni = layer.fieldNameIndex('TA' + current_ID)
        unique_vals = layer.dataProvider().uniqueValues(fni)

        # define categories to use in symbology
        categories = []

        for val in unique_vals:
            int_val = int(val)
            
            
            #Define The Primary Trade Area Colours
            if (int_val == 1):
                
                # initialise the default symbol for this geometry type
                symbol = QgsSymbolV2.defaultSymbol(layer.geometryType())

                # configure a symbol layer
                layer_style = {}
                layer_style['color'] = '%d, %d, %d' % (0, 0, 204)

                layer_style['outline'] = '#000000'
                symbol_layer = QgsSimpleFillSymbolLayerV2.create(layer_style)

                # replace default symbol layer with the configured one
                if symbol_layer is not None:
                    symbol.changeSymbolLayer(0, symbol_layer)
                else:
                    print "success"

                # create renderer object
                category = QgsRendererCategoryV2(val, symbol, str(val))
                # entry for the list of category items
                categories.append(category)
                
            #Define The Secondary Trade Area Colours
            elif (int_val == 2):
                
                # initialise the default symbol for this geometry type
                symbol = QgsSymbolV2.defaultSymbol(layer.geometryType())

                # configure a symbol layer
                layer_style = {}
                layer_style['color'] = '%d, %d, %d' % (102, 178, 255)

                layer_style['outline'] = '#000000'
                symbol_layer = QgsSimpleFillSymbolLayerV2.create(layer_style)

                # replace default symbol layer with the configured one
                if symbol_layer is not None:
                    symbol.changeSymbolLayer(0, symbol_layer)
                else:
                    print "success"

                # create renderer object
                category = QgsRendererCategoryV2(val, symbol, str(val))
                # entry for the list of category items
                categories.append(category)
                
            #Everything else gets skipped, and isn't rendered
            else:
                pass


        # create renderer object
        renderer = QgsCategorizedSymbolRendererV2('TA' + current_ID, categories)

        # assign the created renderer to the layer
        if renderer is not None:
            layer.setRendererV2(renderer)

        layer.triggerRepaint()


# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


# PLEASE OPTIMIZE!!

# Clean Up Temp Files
dir_list = os.listdir(dir_path) 

del(lyrOutput, mem_layer, lyrConsumer, writer_1)

# Delete Centroid Temp File
for items in dir_list:
    if ("Centroids_" + user_filename + ".shp") == items:
        os.remove(path + "Centroids_" + user_filename + ".shp")
        
    elif ("Centroids_" + user_filename + ".dbf") == items:
        os.remove(path + "Centroids_" + user_filename + ".dbf")
        
    elif ("Centroids_" + user_filename + ".prj") == items:
        os.remove(path + "Centroids_" + user_filename + ".prj")
        
    elif ("Centroids_" + user_filename + ".qpj") == items:
        os.remove(path + "Centroids_" + user_filename + ".qpj")
        
    elif ("Centroids_" + user_filename + ".shx") == items:
        os.remove(path + "Centroids_" + user_filename + ".shx")
        
    else:
        pass

# Delete Euclidean Distance Temp File
for items in dir_list:
    if ("EuclideanDistance_DumpLyr_" + user_filename + ".shp") == items:
        os.remove(path + "EuclideanDistance_DumpLyr_" + user_filename + ".shp")
        
    elif ("EuclideanDistance_DumpLyr_" + user_filename + ".dbf") == items:
        os.remove(path + "EuclideanDistance_DumpLyr_" + user_filename + ".dbf")
        
    elif ("EuclideanDistance_DumpLyr_" + user_filename + ".prj") == items:
        os.remove(path + "EuclideanDistance_DumpLyr_" + user_filename + ".prj")
        
    elif ("EuclideanDistance_DumpLyr_" + user_filename + ".qpj") == items:
        os.remove(path + "EuclideanDistance_DumpLyr_" + user_filename + ".qpj")
        
    elif ("EuclideanDistance_DumpLyr_" + user_filename + ".shx") == items:
        os.remove(path + "EuclideanDistance_DumpLyr_" + user_filename + ".shx")
        
    elif ("EuclideanDistance_DumpLyr_" + user_filename + ".cpg") == items:
        os.remove(path + "EuclideanDistance_DumpLyr_" + user_filename + ".cpg")
        
    else:
        pass
















