# Notes about how I developed the AI Konoha Village

## Obtain the "hidden leaf village " 3D model
I downloaded it from here: 

https://mega.nz/file/vkcHSYLT#t5gG06y65gEp8g3U8N8Yic5BijvZ0PA_7UstCmnoG38

https://www.deviantart.com/naruko-uzumaki-the-9/art/Hidden-Leaf-Village-Complete-DL-Fixed-809223977

## Import to blender
In my case, I cannot directly open the files. But I can import the .fbx file in blender 3.6 (mac M1). 
Change the Render Engine from Eevee to Workbench, and then at the Color drop menu, select Texture. Then press "Z" and select "render" model. You will see colored model there.

## import & export .fbx file from blender
When export .fbx file from blender and load to unity, it may encounter errors like mesh tangents or self intersection warning. The way to solve this is:
1. Install Better FBX Importer Exporter plugin for blender (it solves the mesh tangent problem);
2. When export using the plugin, select triangulate (it solves the intersection problem).

## import .fbx or .dae file to unity
I found the best way is directly drag the whole folder including the materials/textures to the asset folder of the unity project. Then unity will load the assets in the folder and generate .meta data. After that, we can drag the assets to the project from the "project" window. Note that seems unity 2022 doesn't show project and inspector windows by default. But unity 2021 can show the windows. For unity 2022, we can select "Window -> Layouts -> Default" to get the desired layout.

I also compared the .dae and .fbx file for the hidden leaf village model. In Unity, seems the "Hidden Leaf Village - Complete.dae" file looks better in Unity.

