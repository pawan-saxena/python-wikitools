CREATE TABLE `coords` (
  `coords_id` INT(10) NOT NULL AUTO_INCREMENT,
  `coords_title` VARCHAR(255) COLLATE utf8_bin NOT NULL,
  `coords_lat` FLOAT NOT NULL,
  PRIMARY KEY  (`coords_id`),
  KEY `coords_lat` (`coords_lat`),
  FULLTEXT KEY `coords_title` (`coords_title`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 COLLATE=utf8_bin;
 
CREATE TABLE `ERRORS` (
  `error_id` INT(10) NOT NULL AUTO_INCREMENT,
  `error_desc` VARCHAR(50) COLLATE utf8_bin NOT NULL,
  `error_lat` VARCHAR(25) COLLATE utf8_bin DEFAULT NULL,
  `error_title` VARCHAR(255) COLLATE utf8_bin DEFAULT NULL,
  PRIMARY KEY  (`error_id`),
  FULLTEXT KEY `error_desc` (`error_desc`,`error_lat`,`error_title`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 COLLATE=utf8_bin;
 
CREATE TABLE `links` (
  `pageid` INT(10) NOT NULL,
  KEY `pageid` (`pageid`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_bin;
