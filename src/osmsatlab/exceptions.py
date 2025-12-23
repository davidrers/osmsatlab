class OSMSatLabError(Exception):
    """Base exception for osmsatlab"""
    pass

class OSMDownloadError(OSMSatLabError):
    """Raised when OSM data download fails"""
    pass

class DataSchemaError(OSMSatLabError):
    """Raised when data does not match expected schema"""
    pass
