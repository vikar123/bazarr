from http.cookiejar import DefaultCookiePolicy
from pydoc import doc
import subprocess              
import logging
import ast
from typing import List
from config import settings
from database import TableEpisodes,TableMovies,TableHistory

class SubTools:
    def __init__(self):
        self.ffmpegmap = None
        self.reference = None
        self.ffmpegsrtout = None       
        self.ffmpegbin = None
        self.ffmpegargs = None
        self.mediatype = None
        self.externalsub = None
        self.embeddedsub = None      
                
    def extractSubtitle(self, input_reference_path, sub_index, srt_out_path, ffmpeg_bin_path):
        self.reference = input_reference_path
        self.ffmpegmap = sub_index
        self.ffmpegsrtout = srt_out_path
        self.ffmpegbin = ffmpeg_bin_path
        self.ffmpegargs = [self.ffmpegbin]
        self.ffmpegargs.extend([
                '-y',
                '-nostdin',
                '-loglevel', 'warning',
                '-i', self.reference,
                '-map', self.ffmpegmap,
                '-f', 'srt',
                self.ffmpegsrtout

            ])
        logging.debug('Running with args {} ...'.format(self.ffmpegargs))
        logging.debug('Attempting to extract subtitles to {} ...'.format(self.ffmpegsrtout))
        retcode = subprocess.call(self.ffmpegargs)
        if retcode == 0:
            logging.info('...done')
            return True
        else:
            return False
    def determineFallBackMethod(self,external,embedded):
        if settings.subsync.getboolean('use_reftrack_embedded_subtitles') == True and \
            settings.subsync.getboolean('use_reftrack_external_subtitles') == True and \
            external == False and embedded == False and settings.subsync.getboolean('use_reftrack_fallback_audio') == False:
                logging.error('No external / Embedded subtitles available. Audio fallback disabled. Quitting...')
                return False
        elif settings.subsync.getboolean('use_reftrack_embedded_subtitles') == True and \
            settings.subsync.getboolean('use_reftrack_external_subtitles') == False and \
            external == False and settings.subsync.getboolean('use_reftrack_fallback_audio') == False:
                logging.error('No external subtitle available. Embedded Subtitles / Audio fallback disabled. Quitting...')
                return False    
        elif settings.subsync.getboolean('use_reftrack_embedded_subtitles') == False and \
            settings.subsync.getboolean('use_reftrack_external_subtitles') == True and \
            embedded == False and settings.subsync.getboolean('use_reftrack_fallback_audio') == False:
                logging.error('No embedded subtitle available. External Subtitles / Audio fallback disabled. Quitting...')
                return False
        else:
            return True      
    def determineSyncMethod(self,external,embedded):
        if settings.subsync.getboolean('use_reftrack_embedded_subtitles') == True and \
            settings.subsync.getboolean('use_reftrack_external_subtitles') == True and \
                embedded == True:
                return 'embedded'
        if settings.subsync.getboolean('use_reftrack_embedded_subtitles') == True and \
            settings.subsync.getboolean('use_reftrack_external_subtitles') == False and \
                embedded == True:
                return 'embedded'
        if settings.subsync.getboolean('use_reftrack_embedded_subtitles') == False and \
            settings.subsync.getboolean('use_reftrack_external_subtitles') == True and \
                external == True:
                return 'external'
        if settings.subsync.getboolean('use_reftrack_embedded_subtitles') == True and \
            settings.subsync.getboolean('use_reftrack_external_subtitles') == True and \
                external == False and embedded == False:
                return 'audio'                  
    def getReferenceSubtitle(self, input_reference, external_dict, embedded_dict, sync_method, srt_out_path, ffmpeg_bin_path):
        self.reference = input_reference
        self.externalDict = external_dict
        self.embeddedDict = embedded_dict
        self.syncMethod = sync_method
        self.srtOutPath = srt_out_path
        self.ffmpegBinPath = ffmpeg_bin_path
        if sync_method == 'external':
            for subIndex, subInfo in self.externalDict.items():
                    if settings.subsync.getboolean('use_reftrack_external_subtitle_threshold'):
                        ScoreDict = TableHistory.select(TableHistory.score)\
                        .where(TableHistory.subtitles_path == str(subInfo['path']))\
                        .dicts().get()
                        externalSubtitleScore = ast.literal_eval(ScoreDict)
                        logging.debug('ExternalSubtitleScore: %s:', externalSubtitleScore)
                        percent_score = round(externalSubtitleScore * 100 / 360, 2)
                        if percent_score < float(settings.subsync.use_reftrack_external_subtitle_threshold):
                            externalReferenceSrt = str(subInfo['path'])
                            return str(subInfo['path'])
                        else:
                            logging.info('Skipping: {0}: Threshold not met'.format(str(subInfo['path'])))
                    elif subInfo['forced'] and subInfo['hi'] == 'False':
                        return str(subInfo['path'])
                    else:
                        return 'error'
        elif sync_method == 'embedded':
            logging.debug('Iterating over subindex to filter out hi/forced: %s:', self.embeddedDict)
            for subIndex, subInfo in self.embeddedDict.items():
                if subInfo['forced'] and subInfo['hi'] == 'False':
                    logging.debug('Index with known good sub in mkv found with ID: %s', subInfo['track'])
                    return str(subInfo['track'])
        else:
            return 'error'
    def getSubtitleByType(self,media_type,sonarr_episode_id,radarr_id):
        """
        Get subtitle dicts from media type.
        """
        self.mediaType = media_type
        self.sonarr_episode_id = sonarr_episode_id
        self.radarr_id = radarr_id
        if self.mediaType == "series":
            subtitleDict = TableEpisodes.select(TableEpisodes.subtitles_extended)\
                .where(TableEpisodes.sonarrEpisodeId == self.sonarr_episode_id).dicts().get('subtitles_extended')
            subtitleDict = ast.literal_eval(subtitleDict)
            if not bool(subtitleDict['external']) and not bool(subtitleDict['embedded']):
                if self.determineFallBackMethod(False,False) == 'audio':
                    return 'audio'
            if bool(subtitleDict['external']) and bool(subtitleDict['external']):
                result = self.determineSyncMethod(True,True)
                return subtitleDict[result], result
            if bool(subtitleDict['external']) and not bool(subtitleDict['external']):
                result = self.determineSyncMethod(True,False)
                return subtitleDict[result], result
            if not bool(subtitleDict['external']) and bool(subtitleDict['external']):
                result = self.determineSyncMethod(False,True)
                return subtitleDict[result], result
            
        if self.mediaType == "movies":
            subtitleDict = TableMovies.select(TableMovies.subtitles_extended)\
                .where(TableMovies.radarrId == self.radarr_id).dicts().get('subtitles_extended')
            subtitleDict = ast.literal_eval(subtitleDict)
            if not bool(subtitleDict['external']) and not bool(subtitleDict['embedded']):
                if self.determineFallBackMethod(False,False):
                    return 'audio'
            if bool(subtitleDict['external']) and bool(subtitleDict['external']):
                result = self.determineSyncMethod(True,True)
                return subtitleDict[result], result
            if bool(subtitleDict['external']) and not bool(subtitleDict['external']):
                result = self.determineSyncMethod(True,False)
                return subtitleDict[result], result
            if not bool(subtitleDict['external']) and bool(subtitleDict['external']):
                result = self.determineSyncMethod(False,True)
                return subtitleDict[result], result
    def getNewSubSyncArgs(reference, srtin, srtout, ffmpeg_path, vad, log_dir_path, mode):
        if mode == "external":
            arglist = reference, '-i', srtin, '-o', srtout, '--ffmpegpath', ffmpeg_path,'--vad', vad, '--log-dir-path', log_dir_path
        if mode == "embedded":
            arglist = reference, '-i', srtin, '-o', srtout, '--ffmpegpath', ffmpeg_path,'--vad', vad, '--log-dir-path', log_dir_path
        if mode == "audio":
            arglist = reference, '-i', srtin, '-o', srtout, '--ffmpegpath', ffmpeg_path,'--vad', vad, '--log-dir-path', log_dir_path

        return arglist
    def getNestedDictValue(d: dict, *keys, default=None):
        """ Safely get a nested value from a dict

        Example:
            config = {'device': None}
            deep_get(config, 'device', 'settings', 'light')
            # -> None
            
        Example:
            config = {'device': True}
            deep_get(config, 'device', 'settings', 'light')
            # -> TypeError

        Example:
            config = {'device': {'settings': {'light': 'bright'}}}
            deep_get(config, 'device', 'settings', 'light')
            # -> 'light'
        """
        try:
            for k in keys:
                d = d[k]
        except KeyError:
            return default
        except TypeError:
            if d is None:
                return default
            else:
                raise
        else:
            return d

subtools = SubTools()
