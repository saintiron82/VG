from validate_exterior import *
class CandidateOracle(BaselineOracle):
    def __init__(self,arrays,upper):
        super().__init__(arrays);a=np.load(upper);self.upper=a['materials'];self.origin=a['origin_cell_xyz'];self.names=a['material_names'].tolist()
        assert a['pitch_m']==PITCH and a['join_y_m']==9.5
        assert self.origin.tolist()==[-200,300,-164] and self.upper.shape==(148,400,328)
        self.low=(-200,0,-164);self.high=(200,448,164)
    def values(self,x,y,z):
        x,y,z=np.broadcast_arrays(x,y,z);out=super().values(x,y,z)
        isupper=y>=304;out[isupper]=-1
        ix=x+200;iy=y-300;iz=z+164
        valid=isupper&(ix>=0)&(ix<400)&(iy>=0)&(iy<148)&(iz>=0)&(iz<328)
        out[valid]=self.upper[iy[valid],ix[valid],iz[valid]]
        return out

