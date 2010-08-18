--
-- Table structure for table `config_requests`
--

DROP TABLE IF EXISTS `config_requests`;
CREATE TABLE IF NOT EXISTS `config_requests` (
  `cr_id` int(11) NOT NULL AUTO_INCREMENT,
  `cr_reqtime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `cr_abbrv` varchar(10) COLLATE utf8_unicode_ci NOT NULL,
  `field` enum('lim','listpage') COLLATE utf8_unicode_ci NOT NULL,
  `change_to` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `editkey` varchar(10) COLLATE utf8_unicode_ci NOT NULL,
  `notes` mediumblob NOT NULL,
  PRIMARY KEY (`cr_id`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `last_run`
--

DROP TABLE IF EXISTS `last_run`;
CREATE TABLE IF NOT EXISTS `last_run` (
  `last` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  PRIMARY KEY (`last`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `project_config`
--

DROP TABLE IF EXISTS `project_config`;
CREATE TABLE IF NOT EXISTS `project_config` (
  `abbrv` varchar(10) COLLATE utf8_unicode_ci NOT NULL,
  `proj_name` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `cat_name` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `listpage` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `lim` int(10) unsigned NOT NULL DEFAULT '500',
  `month_added` date NOT NULL,
  `month_removed` date DEFAULT NULL,
  PRIMARY KEY (`abbrv`),
  UNIQUE KEY `proj_name` (`proj_name`),
  UNIQUE KEY `cat_name` (`cat_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `project_requests`
--

DROP TABLE IF EXISTS `project_requests`;
CREATE TABLE IF NOT EXISTS `project_requests` (
  `pr_id` int(11) NOT NULL AUTO_INCREMENT,
  `pr_reqtime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `pr_proj_name` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `pr_cat_name` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `pr_listpage` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `pr_lim` int(10) unsigned NOT NULL DEFAULT '500',
  `editkey` varchar(10) COLLATE utf8_unicode_ci NOT NULL,
  `notes` mediumblob NOT NULL,
  PRIMARY KEY (`pr_id`),
  KEY `pr_proj_name` (`pr_proj_name`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
