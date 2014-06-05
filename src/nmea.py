# -*- coding: utf-8 -*-
import os
import datetime


class SentenceNotSupported(Exception):
    pass

class InvalidSentenceLength(Exception):
    pass

class InvalidChecksum(Exception):
    pass
        

class NMEABaseSentence(object):
    
    def ll2decimaldegrees(self, value, direction):
        """parse lon/lat values into decimal degrees"""
        value_in=float(value)
    
        if direction == 'S':
            value_in = -value_in
        elif direction == 'W':
            value_in = -value_in
    
        value_degrees = int(value_in/100)
        value_minutes = value_in - value_degrees*100
    
        return value_degrees + (value_minutes/60)
    
    
    def date_and_time2datetime(self, date_value=None, time_value=None):
        """Parse text date and/or time into datetime object"""
        if date_value and time_value:
            # remove fractional portion if it exists
            time_value = time_value.split(".")[0]            
            time_obj = datetime.datetime.strptime(time_value,"%H%M%S")
            idx = 0
            day = int(date_value[idx:idx+2])
            idx += 2
            month = int(date_value[idx:idx+2])
            idx += 2
            year = int(date_value[idx:idx+2]) + 2000 # assuming year 2000        
            result = datetime.datetime(year, month, day, time_obj.hour, time_obj.minute, time_obj.second)
        elif date_value and not time_value:
            idx = 0
            day = int(date_value[idx:idx+2])
            idx += 2
            month = int(date_value[idx:idx+2])
            idx += 2
            year = int(date_value[idx:idx+2]) + 2000 # assuming year 2000        
            result = datetime.date(year, month, day)
        elif time_value and not date_value:
            # remove fractional portion if it exists
            time_value = time_value.split(".")[0]
            result = datetime.datetime.strptime(time_value,"%H%M%S").time()
        return result
    
    
    def _checksum(self, nmea_sentence):
        nmea_sentence = nmea_sentence.strip()
        assert nmea_sentence.startswith("$")
        assert nmea_sentence[-3] == "*"
        
        sentence_checksum = nmea_sentence[-2:].upper()    
        checksum_components = nmea_sentence[1:-3]
        calculated_checksum = 0
        for c in checksum_components:
            calculated_checksum = calculated_checksum ^ ord(c)
        calculated_checksum = hex(calculated_checksum)[2:].upper()
        if not (calculated_checksum == sentence_checksum):
            msg = "calculated({}) != checksum({})".format(calculated_checksum, sentence_checksum)
            raise InvalidChecksum(msg)        
        return checksum_components
        
            

class GPGGASentence(NMEABaseSentence):
    """Global Positioning System Fix Data"""

    def __init__(self, sentence):
        self.parse(sentence)    
    
    def parse(self, sentence): # IGNORE:W0231 - Parent class has no __init__ method.
        sentence_data = self._checksum(sentence)
        expected_comma_count = 14
        sentence = sentence.strip()
        if sentence_data.count(",") == expected_comma_count:
            fieldnames = (
                          "name",
                          "utc",
                          "latitude",
                          "northsouth",
                          "longitude",
                          "eastwest",
                          "quality",
                          "number_of_satellites_in_use",
                          "horizontal_dilution",
                          "altitude",
                          "above_sea_unit",
                          "geoidal_separation",
                          "geoidal_separation_unit",
                          "data_age",
                          "diff_ref_station_id")
            for fieldname, value in zip(fieldnames, sentence_data.split(",")):
                setattr(self, fieldname, value)
                
            if self.latitude.strip() and self.longitude.strip():
                self.latitude = self.ll2decimaldegrees(self.latitude, self.northsouth)
                self.longitude = self.ll2decimaldegrees(self.longitude, self.eastwest)
    
            self.timeOfFix = self.date_and_time2datetime(time_value=self.utc)
            if self.altitude:
                self.altitude = float(self.altitude)
        else:
            raise InvalidSentenceLength("Expected Comma count not found (expected/actual): %d/%d)" % (expected_comma_count,
                                                                                                      sentence.count(",")))
        
        
class GPRMCSentence(NMEABaseSentence):
    """Recommended minimum specific GPS/Transit data"""
    
    def __init__(self, sentence):
        self.parse(sentence)    
    
    def parse(self, sentence): # IGNORE:W0231 - Parent class has no __init__ method.
        sentence_data = self._checksum(sentence)
        expected_comma_count = 11
        if sentence_data.count(",") >= expected_comma_count:
            self.fieldnames = ("name",
                          "timestamp",
                          "validity",
                          "latitude",
                          "northsouth",
                          "longitude",
                          "eastwest",
                          "speedknots",
                          "truecourse",
                          "datestamp",
                          "variation",
                          )
            
            for fieldname, value in zip(self.fieldnames, sentence_data.split(",", expected_comma_count)):
                setattr(self, fieldname, value)
            
            if self.latitude and self.longitude:
                self.ddlat = self.ll2decimaldegrees(self.latitude, self.northsouth)
                self.ddlon = self.ll2decimaldegrees(self.longitude, self.eastwest)    
            self.datetime = self.date_and_time2datetime(self.datestamp, self.timestamp) 
        else:
            raise InvalidSentenceLength("Expected Comma count not found (expected/actual): %d/%d)" % (expected_comma_count,
                                                                                                      sentence.count(",")))
        
class GPGSVSentence(NMEABaseSentence):
    """GPS Satellites in view"""
    
    def __init__(self, sentence):
        self.parse(sentence)
    
    def parse(self, sentence):
        sentence_data = self._checksum(sentence)
        expected_comma_count = 19
        if sentence_data.count(",") == expected_comma_count:
            self.fieldnames = ("name",
                               "total message_numbers",
                               "message_number",
                               "satellites_in_view",
                               "prn_0",
                               "elevation_0",
                               "azimuth_0",
                               "snr_0",
                               "prn_1",
                               "elevation_1",
                               "azimuth_1",
                               "snr_1",
                               "prn_2",
                               "elevation_2",
                               "azimuth_2",
                               "snr_2",
                               "prn_3",
                               "elevation_3",
                               "azimuth_3",
                               "snr_3",                                                                        
                          )
            for fieldname, value in zip(self.fieldnames, sentence_data.split(",", expected_comma_count)): 
                if fieldname in ("name",):
                    setattr(self, fieldname, value)
                elif not value:
                    setattr(self, fieldname, None)
                else:
                    setattr(self, fieldname, int(value))               
        else:
            raise InvalidSentenceLength("Expected Comma count not found (expected/actual): %d/%d)" % (expected_comma_count,
                                                                                                      sentence.count(",")))
    

    def get_satellites_in_view(self):
        """Return top 4 satellite in view readings"""
        for i in range(4):
            yield getattr(self, "prn_{}".format(i)), getattr(self, "elevation_{}".format(i)), getattr(self, "azimuth_{}".format(i)), getattr(self, "snr_{}".format(i))
    
         

class NMEAParser(object):
    """
    NMEA format parser.  
    Returns Sentence objects with parsed datetime, and lon/lat in decimal degrees where appropriate.
    """
    
    def __init__(self, desired_sentences=None):
        if desired_sentences is None:
            desired_sentences = ("$GPGGA", "$GPRMC", "$GPGSV")
        
        # Define parsers here
        self.sentence_objects = {
                                 "$GPGGA": GPGGASentence,
                                 "$GPRMC": GPRMCSentence,        
                                 "$GPGSV": GPGSVSentence,                
                                 }
        self.supported_sentences = self.sentence_objects.keys()
        
        for desired_sentence in desired_sentences:
            if desired_sentence not in self.supported_sentences:
                raise SentenceNotSupported("{} not in {}".format(desired_sentence, self.supported_sentences))
        self.sentences_to_parse = desired_sentences


    def parse_sentence(self, nmea_sentence):
        """returns a single parsed sentence as a sentence object"""
        sentence_obj = None
        for sentence_format in self.sentences_to_parse:            
            if nmea_sentence.startswith(sentence_format):
                sentence_obj = self.sentence_objects[sentence_format](nmea_sentence)    
                break
        return sentence_obj
                                                

    def parse_nmea_file(self, filepath):
        """yields parsed sentence objects"""
        filepath = os.path.abspath(filepath)
        
        with open(filepath, "r") as f:
            for nmea_sentence in f:
                sentence_obj = None
                try:
                    sentence_obj = self.parse_sentence(nmea_sentence)
                except InvalidSentenceLength:
                    continue                    
    
                if sentence_obj:
                    yield sentence_obj
