# Import necessary modules
import geopandas as gpd

# Set filepath
fp = "usa/usa.shp"

# Read file using gpd.read_file()
data = gpd.read_file(fp, rows=10)

asdf