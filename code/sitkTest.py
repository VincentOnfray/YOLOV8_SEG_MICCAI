import SimpleITK as sitk

image = sitk.ReadImage("Sample.png", imageIO="PNGImageIO")
sitk.WriteImage(image, "sample_OUT.png")