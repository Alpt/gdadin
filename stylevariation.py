#!/usr/bin/env python 
#Note: taken from inkscape/extensions/coloreffect,py (with minor changes)
'''
Copyright (C) 2006 Jos Hirth, kaioa.com
Copyright (C) 2007 Aaron C. Spike

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
'''

import simplestyle
import pdb

color_props_fill=('fill:','stop-color:','flood-color:','lighting-color:')
color_props_stroke=('stroke:',)
color_props = color_props_fill + color_props_stroke
opacity_props = 'opacity:'

def apply_colmod(self, nodeList, hsbcoeffs, opacoeff, hsbo_cf):
  for n in nodeList:
      changeStyle(self, n, hsbcoeffs, opacoeff, hsbo_cf)
      apply_colmod(self, n, hsbcoeffs, opacoeff, hsbo_cf)

def changeStyle(self, node, hsbcoeffs, opacoeff, hsbo_cf):
  if node.attrib.has_key('style'): 
    style=node.get('style') # FIXME: this will break for presentation attributes!
    if style!='':
      #inkex.debug('old style:'+style)
      styles=style.split(';')
      for i in range(len(styles)):
        if styles[i].startswith(opacity_props):
                styles[i]=opacity_props+str(opamod(float(styles[i][len(opacity_props):]), opacoeff, hsbo_cf))
        else:
                for c in range(len(color_props)):
                  if styles[i].startswith(color_props[c]):
                    styles[i]=color_props[c]+process_prop(self, styles[i][len(color_props[c]):], hsbcoeffs, hsbo_cf)

      #inkex.debug('new style:'+';'.join(styles))
      node.set('style',';'.join(styles))

def process_prop(self, col, hsbcoeffs, hsbo_cf):
  #debug('got:'+col)
  if simplestyle.isColor(col):
    c=simplestyle.parseColor(col)
    col='#'+colmod(c[0],c[1],c[2], hsbcoeffs, hsbo_cf)
    #debug('made:'+col)
  if col.startswith('url(#'):
    id = col[len('url(#'):col.find(')')]
    newid = self.newid(self.svg_prefixfromtag(id))
    #inkex.debug('ID:' + id )
    path = '//*[@id="%s"]' % id
    for node in self.document.xpath(path, namespaces=inkex.NSS):
      process_gradient(self, node, newid, hsbcoeffs)
    col = 'url(#%s)' % newid
  return col

def process_gradient(self, node, newid, hsbcoeffs, hsbo_cf):
  newnode = copy.deepcopy(node)
  newnode.set('id', newid)
  node.getparent().append(newnode)
  changeStyle(self, newnode, hsbcoeffs, opacoeff, hsbo_cf)
  for child in newnode:
    changeStyle(self, child, hsbcoeffs, opacoeff, hsbo_cf)
  xlink = inkex.addNS('href','xlink')
  if newnode.attrib.has_key(xlink):
    href=newnode.get(xlink)
    if href.startswith('#'):
      id = href[len('#'):len(href)]
      #inkex.debug('ID:' + id )
      newhref = self.newid(self.svg_prefixfromtag(id))
      newnode.set(xlink, '#%s' % newhref)
      path = '//*[@id="%s"]' % id
      for node in self.document.xpath(path, namespaces=inkex.NSS):
        process_gradient(node, newhref)

hsb_chars = {0: 'h', 1: 's', 2: 'b'}
def colmod(r,g,b, (hue_coeff, sat_coeff, bri_coeff), hsbo_cf):
        hsl = rgb_to_hsl(r/255.0, g/255.0, b/255.0)
        hsl[0] = hsl[0]+hue_coeff
        hsl[1] = hsl[1]+sat_coeff
        hsl[2] = hsl[2]+bri_coeff
        for i in range(len(hsl)):
                fidx = hsb_chars[i]+'f'
                cidx = hsb_chars[i]+'c'
                if hsbo_cf[fidx] >= 0 and hsl[i] <= hsbo_cf[fidx]:
                        hsl[i] = hsbo_cf[fidx]
                if hsbo_cf[cidx] >= 0 and hsl[i] >= hsbo_cf[cidx]:
                        hsl[i] = hsbo_cf[cidx]
                if abs(hsl[i]) > 1.0:
                        hsl[i] -= int(hsl[i])
                if hsl[i] < 0:
                        hsl[i]=1.0+hsl[i]
        rgb = hsl_to_rgb(hsl[0], hsl[1], hsl[2])
        return '%02x%02x%02x' % (rgb[0]*255, rgb[1]*255, rgb[2]*255)

def opamod(opa, opacoeff, hsbo_cf):
        opa+=opacoeff
        if hsbo_cf['of'] >=0 and opa <= hsbo_cf['of']:
                opa = hsbo_cf['of']
        if hsbo_cf['oc'] >=0 and opa >= hsbo_cf['oc']:
                opa = hsbo_cf['oc']
        if abs(opa) > 1.0:
                opa -= int(opa)
        if opa < 0:
                opa=1.0+opa
        return opa

def rgb_to_hsl(r, g, b):
  rgb_max = max (max (r, g), b)
  rgb_min = min (min (r, g), b)
  delta = rgb_max - rgb_min
  hsl = [0.0, 0.0, 0.0]
  hsl[2] = (rgb_max + rgb_min)/2.0
  if delta == 0:
      hsl[0] = 0.0
      hsl[1] = 0.0
  else:
      if hsl[2] <= 0.5:
          hsl[1] = delta / (rgb_max + rgb_min)
      else:
          hsl[1] = delta / (2 - rgb_max - rgb_min)
      if r == rgb_max:
          hsl[0] = (g - b) / delta
      else:
          if g == rgb_max:
              hsl[0] = 2.0 + (b - r) / delta
          else:
              if b == rgb_max:
                  hsl[0] = 4.0 + (r - g) / delta
      hsl[0] = hsl[0] / 6.0
      if hsl[0] < 0:
          hsl[0] = hsl[0] + 1
      if hsl[0] > 1:
          hsl[0] = hsl[0] - 1
  return hsl

def hue_2_rgb (v1, v2, h):
  if h < 0:
      h += 6.0
  if h > 6:
      h -= 6.0
  if h < 1:
      return v1 + (v2 - v1) * h
  if h < 3:
      return v2
  if h < 4:
      return v1 + (v2 - v1) * (4 - h)
  return v1

def hsl_to_rgb (h, s, l):
  rgb = [0, 0, 0]
  if s == 0:
      rgb[0] = l
      rgb[1] = l
      rgb[2] = l
  else:
      if l < 0.5:
          v2 = l * (1 + s)
      else:
          v2 = l + s - l*s
      v1 = 2*l - v2
      rgb[0] = hue_2_rgb (v1, v2, h*6 + 2.0)
      rgb[1] = hue_2_rgb (v1, v2, h*6)
      rgb[2] = hue_2_rgb (v1, v2, h*6 - 2.0)
  return rgb
