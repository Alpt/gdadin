#!/usr/bin/env python

import gdadin

class GdadinSetparams(gdadin.Gdadin):
        def effect(self):
                self.setshapecallparams()

e = GdadinSetparams()  
e.affect()
