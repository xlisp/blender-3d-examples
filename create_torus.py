# 保存为 create_torus.py
# 使用方法：blender --background --python create_torus.py

import bpy
import bmesh
import os
from mathutils import Vector

def create_torus_ring(outer_dia=25, inner_dia=20, thickness=2):
    """
    在Blender中创建精确的圆环
    """
    
    # 清除现有对象
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # 计算参数
    outer_radius = outer_dia / 2
    inner_radius = inner_dia / 2
    major_radius = (outer_radius + inner_radius) / 2
    minor_radius = (outer_radius - inner_radius) / 2
    
    # 创建环形
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius,
        minor_radius=minor_radius,
        major_segments=64,
        minor_segments=32,
        location=(0, 0, 0)
    )
    
    # 获取当前对象
    obj = bpy.context.active_object
    
    # 缩放Z轴到指定厚度
    current_height = obj.dimensions.z
    scale_z = thickness / current_height
    
    bpy.ops.transform.resize(value=(1, 1, scale_z))
    
    # 应用变换
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    
    return obj

def export_stl(filename="torus_25x20x2.stl"):
    """
    导出STL文件
    """
    bpy.ops.export_mesh.stl(filepath=filename)
    print(f"STL文件已导出: {filename}")

def main():
    """
    主函数
    """
    # 创建圆环
    torus = create_torus_ring(
        outer_dia=25,  # 外径25mm
        inner_dia=20,  # 内径20mm  
        thickness=2    # 厚度2mm
    )
    
    print("圆环已创建")
    print(f"外径: 25mm")
    print(f"内径: 20mm") 
    print(f"厚度: 2mm")
    print(f"实际尺寸: {torus.dimensions}")
    
    # 导出STL
    export_stl("/Users/xlisp/Desktop/torus_25x20x2.stl")

# 运行脚本
if __name__ == "__main__":
    main()
