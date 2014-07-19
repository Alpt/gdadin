#!/usr/bin/env python
#
#                                  Gdadin 
#                 GUI to Draw Algorithms Designed with Inkscape
#

'''
Copyright (C) 2005 Andrea Lo Pumo aka AlpT <alpt@freaknet.org>

This source code is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License as published 
by the Free Software Foundation; either version 2 of the License,
or (at your option) any later version.

This source code is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
Please refer to the GNU Public License for more details.

You should have received a copy of the GNU Public License along with
this source code; if not, write to:
Free Software Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
'''

# TODO: use threads if possible. (Multi-core CPUs)
# TODO: check the memory available and halt the rendering when it becomes
#       insufficient
# TODO: musical shapes

import inkex, T, stylevariation
import random, copy, sys
from math import sqrt
#import pdb

HSBO_PRECISION=1000.0

def weighted_random_index(weights):
        '''Given a list of weights, chooses a random weighted integer 
            from [0, len(weights)-1]'''
        weights = [ int(w*100) for w in weights ]
        wsum = int(sum(weights))
        wi = random.randint(1, wsum)
        i=ws=0
        for w in weights:
                ws+=w
                if wi <= ws: break
                i+=1
        return i

class Gdadin(inkex.Effect):
        def svg_nodefromid(self, id):
                return self.document.xpath('//*[@id="%s"]' % id, namespaces=inkex.NSS)[0]

        def svg_prefixfromtag(self, name):
                if '{' in name and '}' in name:
                        prefix = name.split('}')[-1]
                else:
                        prefix = name[0]
                return prefix

        def svg_appendnewnode(self, node, name, attrib={}):
                if not attrib or 'id' not in attrib:
                        attrib['id'] = self.newid(self.svg_prefixfromtag(name))
                return inkex.etree.SubElement(node, name, attrib)

        def svg_appendnode(self, node, child):
                node.append(child)

        def svg_getattr(self, node, attribname):
                #Note: returns None if the attribute doesn't exist
                return node.get(attribname)

        def svg_setattr(self, node, attribname, value):
                return node.set(attribname, value)

        def svg_remattr(self, node, attribname):
                del node.attrib[attribname]

        def svg_remnode(self, node):
                parent=node.getparent()
                parent.remove(node)

        def svg_subnodeslist(self, node, id=None):
                return [ child for child in node if not id or child.get('id') == id ]

        def svg_nodename(self, node):
                return node.tag

        def svg_appendnewlink(self, node, hrefid):
                 self.svg_appendnewnode(node, inkex.addNS('use', 'svg'), 
                                        { inkex.addNS('href','xlink'):'#'+hrefid })

        def newid(self, prefix):
                #Note: 2**53 is the maximum of randint
                while 1:
                        id = prefix+str(random.randint(0, 2**53))
                        if not id in self.doc_ids:
                                self.doc_ids[id]=1
                                return id

        def __init__(self):
		inkex.Effect.__init__(self)

                self.rdepth_counter = {}
                self.shape_dimension = {}
                self.gdadin_shapeids = None
                self.cache_nodebyname = {}
                self.cache_idbyname = {}
                self.shape_bbox={}
                self.render_groups=[]

                inkex.NSS[u'gdadin']=u'http://www.inkscape.org/namespaces/inkscape'

		self.OptionParser.add_option("--shapename",
						action="store", type="string", 
						dest="shapename", default="shape"+str(random.randint(0, 2**32-1)),
						help="Shape's name")
		self.OptionParser.add_option("--shapeweight",
						action="store", type="float", 
						dest="shapeweight", default=1.0,
						help="Shape's weight. Used for random calls.")	

       		self.OptionParser.add_option("--scprdepth",
						action="store", type="int", 
                                                dest="scprdepth", default=1,
                                                help="Recursion depth (0 is infinite)")
		## Hue
                self.OptionParser.add_option("--scphue",
						action="store", type="int", 
                                                dest="scphue", default=0,
                                                help="Relative hue change")
		self.OptionParser.add_option("--scphuefloor",
						action="store", type="int", 
                                                dest="scphuefloor", default=-1,
                                                help="Minimum hue value (<0 is disabled)")
		self.OptionParser.add_option("--scphueceil",
						action="store", type="int",
                                                dest="scphueceil", default=-1,
                                                help="Maximum hue value (<0 is disabled)")
                ## Saturation
		self.OptionParser.add_option("--scpsat",
						action="store", type="int", 
                                                dest="scpsat", default=0,
                                                help="Relative saturation change")
		self.OptionParser.add_option("--scpsatfloor",
						action="store", type="int", 
                                                dest="scpsatfloor", default=-1,
                                                help="Minimum sat value (<0 is disabled)")
		self.OptionParser.add_option("--scpsatceil",
						action="store", type="int",
                                                dest="scpsatceil", default=-1,
                                                help="Maximum sat value (<0 is disabled)")

                ## Brightness
		self.OptionParser.add_option("--scpbri",
						action="store", type="int", 
                                                dest="scpbri", default=0,
                                                help="Relative brightness change")
		self.OptionParser.add_option("--scpbrifloor",
						action="store", type="int", 
                                                dest="scpbrifloor", default=-1,
                                                help="Minimum bri value (<0 is disabled)")
		self.OptionParser.add_option("--scpbriceil",
						action="store", type="int",
                                                dest="scpbriceil", default=-1,
                                                help="Maximum bri value (<0 is disabled)")
                
                ## Opacity
		self.OptionParser.add_option("--scpopa",
						action="store", type="int", 
                                                dest="scpopa", default=0,
                                                help="Relative opacity change")
		self.OptionParser.add_option("--scpopafloor",
						action="store", type="int", 
                                                dest="scpopafloor", default=0,
                                                help="Minimum opa value (<0 is disabled)")
		self.OptionParser.add_option("--scpopaceil",
						action="store", type="int",
                                                dest="scpopaceil", default=1000,
                                                help="Maximum opa value (<0 is disabled)")


                chars = ''.join([chr(i) for i in range(65,91)+range(48,58)])
                randomstring = ''.join([random.choice(chars) for i in range(9)])
       	        self.OptionParser.add_option("--renderseed",
						action="store", type="string", 
                                                dest="renderseed", default=randomstring,
                                                help="Random seed")
                self.OptionParser.add_option("--rendermaxshapes",
						action="store", type="int", 
                                                dest="rendermaxshapes", default=0,
                                                help="Maximum number of shapes (0 is infinite)")

        def effect(self):
                pass
        
        def set_gdadin_shapeids(self):
                if self.gdadin_shapeids:
                        return self.gdadin_shapeids

                defs = self.xpathSingle('/svg:svg//svg:defs')
                if defs == None:
                        defs = self.svg_appendnewnode(self.document.getroot(), inkex.addNS('defs','svg'))
                self.gdadin_shapeids = defs.find(inkex.addNS('shapeids','gdadin'))
                if self.gdadin_shapeids == None:
                        self.gdadin_shapeids = self.svg_appendnewnode(defs, inkex.addNS('shapeids','gdadin'))
                else:
                        self.rem_old_shapeids()
                return self.gdadin_shapeids

        def get_gdadin_shapeids(self):
                if self.gdadin_shapeids == None:
                        inkex.debug('WARNING: No shape has been defined yet.')
                        return None
                return self.gdadin_shapeids 

        def add_shapeid(self, sname, sid, sweight):
                '''Adds the shape id `sid' in the gdadin_shapeids node'''
                
                gs = self.get_gdadin_shapeids()
                gss = self.svg_subnodeslist(gs, sname)
                if not gss:
                        n = self.svg_appendnewnode(self.get_gdadin_shapeids(), inkex.addNS('shape','gdadin'), 
                                                        {'id':sname, inkex.addNS('shapeid','gdadin'):sid, 
                                                                inkex.addNS('weight','gdadin'): str(sweight)})
                else:
                        n = gss[0]
                        self.svg_setattr(n, inkex.addNS('shapeid','gdadin'), self.svg_getattr(n, inkex.addNS('shapeid','gdadin')) + ';' + sid)
                        self.svg_setattr(n, inkex.addNS('weight','gdadin'), self.svg_getattr(n, inkex.addNS('weight','gdadin')) + ';' + str(sweight))

        def get_gss(self, sname):
                # Note: an exception occurs if the shape isn't found
                return self.svg_subnodeslist(self.get_gdadin_shapeids(), sname)[0]

        def get_allshapeid(self, sname, gss=None):
                # Note: an exception occurs if the shape isn't found
                if gss == None:
                        gss = self.get_gss(sname)
                return self.svg_getattr(gss, inkex.addNS('shapeid','gdadin')).split(';')

        def get_allshapeweight(self, sname, gss=None):
                # Note: an exception occurs if the shape isn't found
                if gss == None:
                        gss = self.get_gss(sname)
                return [float(n) for n in self.svg_getattr(gss, inkex.addNS('weight','gdadin')).split(';')]

        def rem_old_shapeids(self):
                for gss in self.svg_subnodeslist(self.get_gdadin_shapeids()):
                        gshapeids = self.get_allshapeid(None, gss)
                        weights = [ str(w) for w in self.get_allshapeweight(None, gss) ]
                        d = dict(zip(gshapeids, weights))

                        def is_node_alive(id):
                                try: 
                                        self.svg_nodefromid(id)
                                        return True
                                except:
                                        return False
                       
                        for id in d.keys():
                                if not is_node_alive(id):
                                        del d[id]

                        if not len(d):
                                # the shape has been completely removed
                                self.svg_remnode(gss)
                        else:
                                self.svg_setattr(gss, inkex.addNS('shapeid','gdadin'), ';'.join(d.keys()))
                                self.svg_setattr(gss, inkex.addNS('weight','gdadin'), ';'.join(d.values()))

        def init_shape_cache(self):
                allnodes = self.svg_subnodeslist(self.get_gdadin_shapeids())
                cache_shapenames = [self.svg_getattr(sn, 'id') for sn in allnodes]

                cache_shapeids     = [self.get_allshapeid(sname) for sname in cache_shapenames]
                cache_shapeweights = [self.get_allshapeweight(sname) for sname in cache_shapenames]
                cache_shapenodes = [[ self.svg_nodefromid(sid) for sid in sids ] for sids in cache_shapeids]

                self.cache_nodebyname = dict(zip(cache_shapenames, cache_shapenodes)) 
                self.cache_idbyname = dict(zip(cache_shapenames,  cache_shapeids)) 
                self.cache_weightbyname = dict(zip(cache_shapenames, cache_shapeweights)) 



        def get_shapenode(self, sname):
                # Note: an exception occurs if the shape isn't found
                if not self.cache_nodebyname:
                        self.init_shape_cache()

                return self.cache_nodebyname[sname][weighted_random_index(self.cache_weightbyname[sname])]

        def at_least_one(self):
                if len(self.selected) < 1:
                       inkex.debug('Nothing to do: you have to select at least one object.')
                       return 1
                return 0

        def defshape(self):
               if self.at_least_one(): return

               self.set_gdadin_shapeids()

               # create the shape group
               firstnode=self.selected.items()[0][1]
               '''
               if len(self.selected) == 1 and self.svg_getattr(firstnode, inkex.addNS('shape','gdadin')):
                       sgroup = firstnode
                       del self.selected[self.selected.items()[0][0]]
               else:
               '''
               sgroup = self.svg_appendnewnode(firstnode.getparent(),
                                                 inkex.addNS('g','svg'), 
                                                 {inkex.addNS('shape','gdadin'): self.options.shapename})

               for id, node in self.selected.iteritems():
#approach1                       self.svg_appendnode(sgroup, node)
#approach2                       self.svg_appendnewlink(sgroup, id)
#approach3
                      cn = copy.deepcopy(node)
                      self.svg_setattr(cn, 'id', self.newid(self.svg_prefixfromtag(cn.tag)))
                      self.svg_appendnode(sgroup, cn)

               # Update the shapes index
               sgroupid=self.svg_getattr(sgroup, 'id')
               self.add_shapeid(self.options.shapename, sgroupid, self.options.shapeweight)

        def foreach_selected(self, f, args=None):
                for id, node in self.selected.iteritems():
                        shapename = self.svg_getattr(node, inkex.addNS('shape','gdadin'))
                        if not shapename:
                                inkex.debug('WARNING: one of the selected objects isn\'t a defined shape (use Gdadin -> Define Shape).  I\'ll ignore it.')
                                continue
            
                        if args:
                                f(id, node, shapename, *args)
                        else:
                                f(id, node, shapename)

        def setshapecallparams(self):
                if self.at_least_one(): return

                self.set_gdadin_shapeids()
                
                def setallattr(id, node, shapename):
                        self.svg_setattr(node, inkex.addNS('rdepth','gdadin'), str(self.options.scprdepth))

                        self.svg_setattr(node, inkex.addNS('hue','gdadin'), str(self.options.scphue/HSBO_PRECISION))
                        self.svg_setattr(node, inkex.addNS('huefloor','gdadin'), str(self.options.scphuefloor/HSBO_PRECISION))
                        self.svg_setattr(node, inkex.addNS('hueceil','gdadin'), str(self.options.scphueceil/HSBO_PRECISION))

                        self.svg_setattr(node, inkex.addNS('sat','gdadin'), str(self.options.scpsat/HSBO_PRECISION))
                        self.svg_setattr(node, inkex.addNS('satfloor','gdadin'), str(self.options.scpsatfloor/HSBO_PRECISION))
                        self.svg_setattr(node, inkex.addNS('satceil','gdadin'), str(self.options.scpsatceil/HSBO_PRECISION))

                        self.svg_setattr(node, inkex.addNS('bri','gdadin'), str(self.options.scpbri/HSBO_PRECISION))
                        self.svg_setattr(node, inkex.addNS('brifloor','gdadin'), str(self.options.scpbrifloor/HSBO_PRECISION))
                        self.svg_setattr(node, inkex.addNS('briceil','gdadin'), str(self.options.scpbriceil/HSBO_PRECISION))

                        self.svg_setattr(node, inkex.addNS('opa','gdadin'), str(self.options.scpopa/HSBO_PRECISION))
                        self.svg_setattr(node, inkex.addNS('opafloor','gdadin'), str(self.options.scpopafloor/HSBO_PRECISION))
                        self.svg_setattr(node, inkex.addNS('opaceil','gdadin'), str(self.options.scpopaceil/HSBO_PRECISION))

                self.foreach_selected(setallattr)

        def apply_hsbo(self, node, pnode, rdata):
                stylevariation.apply_colmod(self, node, (rdata['hue'], rdata['sat'], rdata['bri']), rdata['opa'], rdata)

        def foreach_subshape(self, rootnode, f, args=None):
                for parentnode in self.svg_subnodeslist(rootnode):
                        childsname = self.svg_getattr(parentnode, inkex.addNS('shape','gdadin'))
                        if not childsname:
                                continue
                        try:
                                childsnode = self.get_shapenode(childsname)
                        except:
                                continue
#                                sys.exit('ERROR: one of the defined shape isn\'t available (has it been deleted?). Aborting.')

                        if args:
                                f(rootnode, parentnode, childsname, childsnode, *args)
                        else:
                                f(rootnode, parentnode, childsname, childsnode)

        def compute_shape_bbox(self, id, node, shapename):
                self.shape_bbox[id] = T.computeBBox(node)
                return self.shape_bbox[id]
        def bbox_diagonal_length(self, bbox):
                x1,y1,x2,y2=(bbox[0], bbox[2], bbox[1], bbox[3])
                return sqrt((x1-x2)**2+(y1-y2)**2)
        def bbox_apply_mat(self, bbox, mat):
                A=[0,0]
                B=[0,0]
                A[0],A[1],B[0],B[1]=(bbox[0], bbox[2], bbox[1], bbox[3])
                T.applyTransformToPoint(mat, A)
                T.applyTransformToPoint(mat, B)
                return min(A[0], B[0]), max(A[0], B[0]), min(A[1], B[1]), max(A[1], B[1])

        def check_shape_size(self, id, mat):
                '''Returns 1 if the shape is too small to be seen'''
                bbox = self.bbox_apply_mat(self.shape_bbox[id], mat)
                if self.bbox_diagonal_length(bbox) < 1:
                        return 1
                return 0

        def adjust_document_dim(self):
                bbox = T.computeBBox(self.render_groups)
                width = bbox[1] - bbox[0] + 100
                height = bbox[3] - bbox[2] + 100
                translateX = -bbox[0]+50
                translateY= -bbox[2]+50

                root = self.document.getroot()
                self.svg_setattr(root, 'width', str(width))
                self.svg_setattr(root, 'height', str(height))
                
                T.applyTransformToNode([[1,0,translateX],[0,1,translateY]], self.current_layer)
        
        def add_rendergroup(self, id, node, shapename):
                rgroup = self.svg_appendnewnode(node.getparent(), inkex.addNS('g','svg'),
                                                {inkex.addNS('render','gdadin'):'1',
                                                inkex.addNS('seed', 'gdadin'): self.options.renderseed}
                                                )
                self.svg_appendnode(rgroup, node)
                self.render_groups.append(rgroup)

        def render(self):
                if self.at_least_one(): return
                
                random.seed(self.options.renderseed)

                self.set_gdadin_shapeids()
                
                self.render_stack=[]
                
                recursedata = { 'firstid' : None,
                                'mat'     : None,
                                'hue'     : 0.0,
                                'sat'     : 0.0,
                                'bri'     : 0.0,
                                'opa'     : 0.0,

                                'hf'      : -1,
                                'hc'      : -1,
                                'sf'      : -1,
                                'sc'      : -1,
                                'bf'      : -1,
                                'bc'      : -1,
                                'of'      : 0,
                                'oc'      : 1
                              }

                def doit(id, node, shapename, rdata):
                        self.compute_shape_bbox(id, node, shapename)
                        self.add_rendergroup(id, node, shapename)
                        self.render_shape(id, node, shapename, rdata)
                self.foreach_selected(doit, (recursedata,))
                
                nshapes=0
                maxnshapes=int(self.options.rendermaxshapes)
                while len(self.render_stack):
                        if maxnshapes and nshapes > maxnshapes:
                                inkex.debug('Maximum number of shapes reached ('+str(maxnshapes)+')')
                                break
                        args=self.render_stack.pop(0)
                        self._render_shape(*args)
                        nshapes+=1
        
                if nshapes:
                        self.adjust_document_dim() 

        def render_shape(self, id, node, shapename, rdata):
                self.render_stack.append((id, node, shapename, rdata))
        
        def _render_shape(self, id, node, shapename, rdata):
                #Note: `shapename' is not used
                if rdata['firstid'] == None: rdata['firstid'] = id

                ## Affine transform
                nmat = T.parseTransform(node.get('transform'))
                if rdata['mat']:
                        rdata['mat'] = T.composeTransform(rdata['mat'], nmat)
                        T.writeTransformToNode(rdata['mat'], node)
                else:
                        rdata['mat'] = nmat

                if self.check_shape_size(rdata['firstid'], rdata['mat']):
                        return #ok, let's stop

                self.foreach_subshape(node, self.call_shape, (rdata,))
        
        def check_rdepth(self, parentnode):
                pid = self.svg_getattr(parentnode, 'id')
                try:
                        rdepth_max = int(self.svg_getattr(parentnode, inkex.addNS('rdepth','gdadin')))
                except:
                        #no depth to care about
                        return 1 # go on

                if not pid in self.rdepth_counter:
                        self.rdepth_counter[pid]=0
                if rdepth_max and self.rdepth_counter[pid] >= rdepth_max-1:
                        return 0 # stop
                self.rdepth_counter[pid]+=1
                return 1 # go on

        def call_shape(self, rootnode, parentnode, childsname, childsnode, rdata):
                '''Inside `rootnode', substitute the `parentnode' with
                `childsnode', but keep the transformation attribute'''
               
                if not self.check_rdepth(parentnode):
                        return

                nrdata = dict(rdata)

                childid = self.svg_getattr(childsnode, 'id')
                if childid in self.rdepth_counter:
                        self.rdepth_counter[self.svg_getattr(childsnode, 'id')]+=1

                newchild = copy.deepcopy(childsnode)
                self.svg_setattr(newchild, 'id', self.newid(self.svg_prefixfromtag(childsnode.tag)))
                try:
                        self.svg_remattr(newchild, inkex.addNS('shape','gdadin'))
                        self.svg_remattr(newchild, 'transform')
                except:
                        pass
                #inkex.debug('calling ' + childsname + ' by ' + parentnode.get('id') +' in '+rootnode.get('id')+' newchild is '+newchild.get('id'))

                ### Calculate the various transformations.
                pmat = T.parseTransform(self.svg_getattr(parentnode, 'transform'))
                nrdata['mat'] = T.composeTransform(nrdata['mat'], pmat)

                ## Hue, Saturation, Brightness, Opacity
                try:
                        nrdata['hue']+=float(self.svg_getattr(parentnode, inkex.addNS('hue','gdadin')))
                        nrdata['sat']+=float(self.svg_getattr(parentnode, inkex.addNS('sat','gdadin')))
                        nrdata['bri']+=float(self.svg_getattr(parentnode, inkex.addNS('bri','gdadin')))
                        nrdata['opa']+=float(self.svg_getattr(parentnode, inkex.addNS('opa','gdadin')))
                        nrdata['hf'] = float(self.svg_getattr(parentnode, inkex.addNS('huefloor','gdadin')))
                        nrdata['hc'] = float(self.svg_getattr(parentnode, inkex.addNS('hueceil','gdadin')))
                        nrdata['sf'] = float(self.svg_getattr(parentnode, inkex.addNS('satfloor','gdadin')))
                        nrdata['sc'] = float(self.svg_getattr(parentnode, inkex.addNS('satceil','gdadin')))
                        nrdata['bf'] = float(self.svg_getattr(parentnode, inkex.addNS('brifloor','gdadin')))
                        nrdata['bc'] = float(self.svg_getattr(parentnode, inkex.addNS('briceil','gdadin')))
                        nrdata['of'] = float(self.svg_getattr(parentnode, inkex.addNS('opafloor','gdadin')))
                        nrdata['oc'] = float(self.svg_getattr(parentnode, inkex.addNS('opaceil','gdadin')))
                except:
                        pass
                ###

                if nrdata['hue'] or nrdata['sat'] or nrdata['bri'] or nrdata['opa']:
                        self.apply_hsbo(newchild, parentnode, nrdata)
                        hsbo = 1
                else:
                        hsbo = 0

                # xlinkify
                if not hsbo:
                        for sn in self.svg_subnodeslist(newchild):
                                if not self.svg_getattr(sn, inkex.addNS('shape','gdadin')):
                                        self.xlinkify(newchild, sn)

                self.svg_appendnode(rootnode.getparent(), newchild)
                if self.svg_getattr(rootnode, 'id') != nrdata['firstid']:
                        self.svg_remnode(parentnode)

                # Recurse!
                self.render_shape(None, newchild, None, nrdata)

        def xlinkify(self, node, subnode):
                 id = self.svg_getattr(subnode, 'id')
                 self.svg_appendnewlink(node, id)
                 self.svg_remnode(subnode)

if __name__ == '__main__':
        e = Gdadin()
        e.affect()
