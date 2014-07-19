#!/usr/bin/env python

import gdadin

class GdadinRender(gdadin.Gdadin):
        def effect(self):
                self.render()

e = GdadinRender()  
e.affect()
