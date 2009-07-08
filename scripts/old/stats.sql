--
-- Database: `stats`
--

-- --------------------------------------------------------

--
-- Table structure for table `popularity`
--

DROP TABLE IF EXISTS `popularity`;
CREATE TABLE `popularity` (
  `title` varchar(255) collate utf8_bin NOT NULL,
  `hash` varchar(32) collate utf8_bin NOT NULL,
  `hits` int(10) NOT NULL default '0',
  `project_assess` blob NOT NULL,
  UNIQUE KEY `title` (`title`),
  UNIQUE KEY `hash` (`hash`),
  KEY `project_asssess_hits` (`hits`,`project_assess`(767))
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin ROW_FORMAT=DYNAMIC;

-- --------------------------------------------------------

--
-- Table structure for table `popularity_copy`
--

DROP TABLE IF EXISTS `popularity_copy`;
CREATE TABLE `popularity_copy` (
  `title` varchar(255) collate utf8_bin NOT NULL,
  `hash` varchar(32) collate utf8_bin NOT NULL,
  `hits` int(10) NOT NULL default '0',
  `project_assess` blob NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin ROW_FORMAT=DYNAMIC;

-- --------------------------------------------------------

--
-- Table structure for table `redirect_map`
--

DROP TABLE IF EXISTS `redirect_map`;
CREATE TABLE `redirect_map` (
  `target_hash` varchar(32) collate utf8_bin NOT NULL,
  `rd_hash` varchar(32) collate utf8_bin NOT NULL,
  PRIMARY KEY  (`rd_hash`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;
