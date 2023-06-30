import SimpleITK as sitk
import sys
import os
import random
isWindows = sys.platform.__contains__("win")
sep = os.path.sep #path separator


def loaddingList(relativeFolderPath,phase= None,absolute_path=''): 
    ''' 
    args : path to check, phase ('init' => check in the directory, else => check in ./images and ./labels of the directory)
    exit : dictionary{"flair":[list of flair path in dir],"seg":[list of labels path in dir]} p
    '''
    if(len(absolute_path)==0):
        absolute_path = os.path.dirname(__file__)

    dir_abs_path = os.path.join(absolute_path, relativeFolderPath)
    flair=[]
    seg=[]
    dic = {"flair":[],"seg":[]}

    if phase == 'init':
        pathList = os.listdir(dir_abs_path)
        for path in pathList:
            #print(path)
            if (path!=('train'))&(path!=('val'))&(path!=('test')):
                if("FLAIR" in path):
                    #print((((path.rsplit('_', 1))[1]).rsplit('.',2))[0])
                    flair.append(dir_abs_path+sep+path)
                else :
                    seg.append(dir_abs_path+sep+path)

        print(f"Flair/segments:  {str(len(flair))}/{str(len(seg))}" )
        if len(flair) !=len(seg):
            #print(len(flair))
            #print(len(seg))
            print ("ERROR: not the same amout of segments and flaires")
            exit(1)
    
    else : 
        pathList = os.listdir(f"{dir_abs_path}{sep}images")+os.listdir(f"{dir_abs_path}{sep}labels")

        for path in pathList:
                if("FLAIR" in path):
                    flair.append(f"{dir_abs_path}{sep}images{sep}{path}")
                else :
                    seg.append(f"{dir_abs_path}{sep}labels{sep}{path}")

    flair.sort()
    seg.sort()
    
    #print("flair: "+str(len(flair)))
    #print("seg: "+str(len(seg)))
    dic['flair']=flair
    dic['seg']=seg

    return dic

def repartitor(dic,relative_path):

    print('IsWindows: '+str(isWindows))
    
    ''' 
    args : dictionary{"flair":[list of flair path in dir],"seg":[list of labels path in dir]}, dir path contening 'test', 'val', 'train'
    exit : none
    aim : split and move dataset into train, test and val
    '''
    print("Repartition de "+str(len(dic['flair']))+" images")
    taille = len(dic['flair'])

    if taille!=0 :
        database = ['test','train','val']
        repartition = [0,int(taille*0.2),int(taille*0.2)+int(taille*0.8*0.8),taille]

        for i in range(len(repartition)-1):
            for j in range(repartition[i],repartition[i+1]):

                #Move flair file
                old_file = dic['flair'][j]
                old_file_name = str(old_file).split(sep)[-1]
                destination = f"{relative_path}{sep}{database[i]}{sep}images{sep}{old_file_name}"
                os.rename(old_file, destination)

                #Move seg file
                old_file = dic['seg'][j]
                old_file_name = str(old_file).split(sep)[-1]
                destination = f"{relative_path}{sep}{database[i]}{sep}labels{sep}{old_file_name}"
                os.rename(old_file, destination)
                

def reachSeuil(seuil,img,peak):
    ''' 
    args : seuil(int btwin 0 and 100), img(sitk.image), peak(int)
    exit : bool
    aim : says if (labeled pixels/pixels) >= seuil
    '''
    sumFilter = sitk.StatisticsImageFilter()
    x_slice = img.GetWidth()
    y_slice = img.GetHeight()
    nbPixels = int(x_slice*y_slice)
    sumFilter.Execute(img[:,:,peak])
    sge = sumFilter.GetSum()
    if (sge*100/nbPixels)>= seuil:
        return True
    return False

def seuilMax(img, nb_of_slice):
    ''' 
    args : nb_of_slice(int), img(sitk.image)
    exit : float
    aim : return the max seuil askable to have nb_of_slice minimum extract from the image
    '''

    sumFilter = sitk.StatisticsImageFilter()
    x_slice = img.GetWidth()
    y_slice = img.GetHeight()
    z_slice = img.GetDepth()
    nbPixels = int(x_slice*y_slice)
    data=[]
    max = -1
    if nb_of_slice>z_slice:
        print("ERROR: nb of silce > depth")
        exit(1)
    for z in range(z_slice):    # for all slices
        sumFilter.Execute(img[:,:,z])
        sge = sumFilter.GetSum()   # calculate the number of segmented pixels
        sgeProp = sge*100/nbPixels
        data.append(sgeProp)  # push the % ratio of slice (ie the number of segmented pixel of the current slice)
    data.sort(reverse=True)   # sort in descending order the ratio of all slices
    max= data[int(seuil)]     # get the ratio that warrants to have at max "seuil" images
    return max

def emptyFolder(dirPath):
    for filename in os.listdir(dirPath):
        file_path = os.path.join(dirPath, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
           
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))
            
def slicer_main(relativeFolderPath, seuil, testSeuil=False, forceAbsPath=''):
    path_img_dic=loaddingList(relativeFolderPath,'init',forceAbsPath)
    repartitor(path_img_dic,relativeFolderPath)

    testResult=[]
    database = ['test','val','train']
    PatientID = 0
    for folder in database:
        
        path_img_dic = loaddingList(f"{relativeFolderPath}{sep}{folder}",None,forceAbsPath)
        print('[Folder]: '+folder)
        #os.system("rm -r "+relativeFolderPath[: -4]+'/refined/'+folder+'/images/*')
        #os.system("rm -r "+relativeFolderPath[: -4]+'/refined/'+folder+'/labels/*')

        emptyFolder(f"{relativeFolderPath[: -4]}{sep}refined{sep}{folder}{sep}images{sep}")
        emptyFolder(f"{relativeFolderPath[: -4]}{sep}refined{sep}{folder}{sep}labels{sep}")
        #print(len(path_img_dic['flair']))


        for i in range(int(len(path_img_dic['flair']))):
            path = path_img_dic['seg'][i]
            pathFlair = path_img_dic['flair'][i]
            print("[Patient ID: ",PatientID,"]", pathFlair)
            
            nPatient= "Patient_"+str(PatientID)
            PatientID += 1
            
            imgSeg = sitk.ReadImage(path)
            
            if testSeuil == True:
                    
                    maxSeg = seuilMax(imgSeg,seuil)
                   
                    testResult.append(maxSeg)
                    #print("seg "+ str(i)+" : seuil max ="+str(maxSeg)+" pour "+str(seuil)+" img/seg")
            else:
                castFilter = sitk.CastImageFilter()
                imgFlair = sitk.ReadImage(pathFlair)
                z_slice=imgSeg.GetDepth()
                nbOfSlice = 0
                size = list(imgSeg.GetSize())
                if len(size)==3:
                    size[2]=0
                Extractor = sitk.ExtractImageFilter()  
                peaklog = [i for i in range(z_slice)]

                while(nbOfSlice<int(testSeuil)) & (peaklog!=[]):
                    peak = random.randint(0,len(peaklog)-1)

                    if (reachSeuil(seuil, imgSeg, peaklog[peak])):
                        nbSlice=peaklog[peak]
                        strSegList=path.split(sep)
                        newSegPath=""
                        strFlairList=pathFlair.split(sep)
                        newFlairPath=""
                        

                        for j in range(len(strSegList)):
                           #print(f"iteration_{j}")
                            
                            
                            if strSegList[j] == 'raw':
                                print(nPatient)
                                newSegPath = str(f"{newSegPath}{sep}refined{sep}{folder}{sep}labels{sep}MICCAI_{nPatient}_e{str(nbSlice)}.png")
                                break
                            else:
                                newSegPath = f"..{sep}{str(strSegList[j])}"

                                                  
                        

                        for j in range(len(strFlairList)):
                            if strFlairList[j] == 'raw':
                               
                                
                                newFlairPath = str(f"{newFlairPath}{sep}refined{sep}{folder}{sep}images{sep}MICCAI_{nPatient}_e{str(nbSlice)}.png")
                               
                                break
                            else:
                                
                                newFlairPath = f"..{sep}{str(strFlairList[j])}"
                        
                        index = [0, 0, nbSlice]
                        Extractor.SetSize(size)
                        Extractor.SetIndex(index)

                        #print("newSegPath: "+newSegPath)
                        #print("newFlairPath: "+newFlairPath)

                        castFilter.SetOutputPixelType(sitk.sitkUInt8)
                        imgFlair = sitk.RescaleIntensity(imgFlair,0,255)
                        imgFlairSmooth = castFilter.Execute(imgFlair)

                        castFilter.SetOutputPixelType(sitk.sitkUInt8)
                        imgSegSmooth = castFilter.Execute(imgSeg)

                        v1 = Extractor.Execute(imgSegSmooth)
                        str1 =str(newSegPath)
                        #print(str1)
                        #print("v1.GetSize() : ", v1.GetSize())
                        #print("v1.GetPixelIDTypeAsString() : ", v1.GetPixelIDTypeAsString())
                        sitk.WriteImage(v1, str1)
                        

                        v2 = Extractor.Execute(imgFlairSmooth)
                        str2 = str(newFlairPath)
                        sitk.WriteImage(v2, str2)

                        nbOfSlice = nbOfSlice +1
                        

                        del(peaklog[peak])

                    else:
                        del(peaklog[peak])
        
        if testSeuil == True:
            testResult.sort()
            if len(testResult)>0:
                print("seuil max de "+folder+" pour "+str(seuil)+" img/seg = "+str(testResult[0])+"%")

    print("[DONE]")
    
    
path_vers_datasets_raw = f'..{sep}datasets{sep}raw' #chemin relatif vers le répertoire dataset/raw
seuil = 0 #seuil disciminant pour la sélection des coupes (int entre 1 et 100 => rapport nb pixels segementés/nb pixels)
nb_coupe_par_scan = 50 #nb de coupes max extraites par fichier .nii.gz
#print(os.path.isdir("../datasets/raw/test"))

print('#_____________SELECTION_____________#')
slicer_main(path_vers_datasets_raw, seuil, nb_coupe_par_scan,forceAbsPath = f'/home/jovyan/workspace/Yolov8/YOLOV8_SEG_MICCAI/code')