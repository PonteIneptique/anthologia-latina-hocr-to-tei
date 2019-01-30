<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:tei="http://www.tei-c.org/ns/1.0" xpath-default-namespace="http://www.tei-c.org/ns/1.0" xmlns:my="LOCALHOST"
    exclude-result-prefixes="xs"
    version="2.0">
    <xsl:output method="text" indent="no" encoding="UTF-8"/>
    
    <xsl:function name="my:normalize">
        <xsl:param name="string" />
        <xsl:value-of select="replace(replace(translate($string,'&#7491;&#7495;&#7580;&#7496;','abcd'),'\[',' \\lbrack '), '\]', ' \\rbrack ')"/>
    </xsl:function> 
    <xsl:template match="TEI"><xsl:apply-templates select="text/body" /></xsl:template>
    
   <xsl:template match="body"><xsl:text>\documentclass[11pt, a4paper]{report}
\usepackage[utf8x]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage[french]{babel}
\usepackage{verse}
\usepackage{marginnote}
    
\begin{document}
\poemlines{5}
</xsl:text>
<xsl:apply-templates />        
<xsl:text>\end{document} </xsl:text>
        
   </xsl:template>           
    
   <xsl:template match="fw">
       <xsl:text>\begin{center} \textbf{</xsl:text>
       <xsl:value-of select="my:normalize(.)"/>
       <xsl:text>}</xsl:text><xsl:text> \end{center}</xsl:text>
   </xsl:template>
    
   <xsl:template match="pb[@type='page']">
      <xsl:text> \marginpar{[</xsl:text>
      <xsl:value-of select="@n"/>
       <xsl:text>]} </xsl:text>
   </xsl:template> 
    
  <xsl:template match="div[@type='textpart']">
      <xsl:text>\subsection*{</xsl:text>
      <xsl:value-of select="my:normalize(@n)"/>
      <xsl:text>}</xsl:text>
      \begin{verse}
      <xsl:apply-templates select=".//(head|l[not(empty(text()))]|note|pb|fw)"/>
      \end{verse}
  </xsl:template>
    
    <xsl:template match="head">
        <xsl:text>\poemtitle{</xsl:text><xsl:value-of select="my:normalize(.)"/><xsl:text>}</xsl:text>
    </xsl:template>
    
    <xsl:template match="pb[@type='image']">
        ﻿\pagebreak 
    </xsl:template>  
    
  <xsl:template match="l">
      <xsl:apply-templates mode="line"/><xsl:if test="following-sibling::node()"><xsl:text> \\ </xsl:text></xsl:if>
  </xsl:template>
    <xsl:template match="text()">
        <xsl:value-of select="." />
    </xsl:template>
    <xsl:template mode="line" match="text()">
        <xsl:value-of select="my:normalize(.)"/>
    </xsl:template>
    <xsl:template mode="line" match="gap">
        <xsl:text> \lbrack ... \rbrack </xsl:text> 
    </xsl:template>
    <xsl:template match="note">
        <xsl:value-of select="my:normalize(.)"/><xsl:text> \\ </xsl:text>
    </xsl:template>
    
 <xsl:template match="note[@type='Side note']">
     ﻿<xsl:text>\reversemarginpar\marginpar{</xsl:text><xsl:value-of select="my:normalize(.)"/><xsl:text>} </xsl:text>
 </xsl:template>
   
</xsl:stylesheet>
