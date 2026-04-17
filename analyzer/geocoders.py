from geopy.geocoders import GeoNames
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

class GeoNamesUK(GeoNames):
    """
    Custom GeoNames adapter that forces Ukrainian language support.
    """
    def _call_geocoder(self, url, *args, **kwargs):
        url_parts = list(urlparse(url))
        query = dict(parse_qsl(url_parts[4]))
        query['lang'] = 'uk'
        url_parts[4] = urlencode(query)
        new_url = urlunparse(url_parts)
        return super()._call_geocoder(new_url, *args, **kwargs)
