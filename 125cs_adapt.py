import bpy
import bmesh
import mathutils
import math
import os

def clear_scene():
    """清除场景中的所有对象"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

def create_cs_extension_ring():
    """创建CS转接环 - 空心带内螺纹"""
    
    # CS接口标准尺寸
    cs_diameter = 25.4            # CS标准直径
    outer_diameter = 30.0         # 外径
    ring_thickness = 3.0          # 厚度
    thread_pitch = 0.794          # CS螺距
    thread_depth = 0.4            # 螺纹深度
    
    print(f"创建CS转接环: 内径{cs_diameter}mm, 外径{outer_diameter}mm, 厚度{ring_thickness}mm")
    
    # 1. 创建主体圆环（外圆柱）
    bpy.ops.mesh.primitive_cylinder_add(
        radius=outer_diameter/2,
        depth=ring_thickness,
        vertices=64,
        location=(0, 0, 0)
    )
    main_ring = bpy.context.active_object
    main_ring.name = "CS_Ring_Outer"
    
    # 2. 创建基本内孔（稍小，为螺纹留空间）
    base_inner_radius = cs_diameter/2 - thread_depth
    bpy.ops.mesh.primitive_cylinder_add(
        radius=base_inner_radius,
        depth=ring_thickness + 0.2,  # 稍微长一点确保完全穿透
        vertices=64,
        location=(0, 0, 0)
    )
    base_hole = bpy.context.active_object
    base_hole.name = "Base_Hole"
    
    # 先用基本孔挖空主体
    bool_modifier_base = main_ring.modifiers.new(name="Boolean_Base_Hole", type='BOOLEAN')
    bool_modifier_base.operation = 'DIFFERENCE'
    bool_modifier_base.object = base_hole
    bool_modifier_base.solver = 'EXACT'
    
    # 应用基本孔布尔运算
    bpy.context.view_layer.objects.active = main_ring
    bpy.ops.object.modifier_apply(modifier="Boolean_Base_Hole")
    
    # 删除基本孔辅助对象
    bpy.ops.object.select_all(action='DESELECT')
    base_hole.select_set(True)
    bpy.ops.object.delete()
    
    print("基本孔创建完成，现在添加螺纹...")
    
    # 3. 创建螺纹几何并添加到内壁
    create_internal_threads_additive(main_ring, cs_diameter, ring_thickness, thread_pitch, thread_depth)
    
    return main_ring

def create_internal_threads_additive(main_obj, diameter, thickness, pitch, thread_depth):
    """创建螺纹几何，然后加到内壁上"""
    
    inner_radius = diameter/2 - thread_depth
    outer_radius = diameter/2
    
    num_turns = thickness / pitch
    segments_per_turn = 32
    total_segments = int(num_turns * segments_per_turn)
    
    print(f"创建螺纹: {num_turns:.2f}圈, {total_segments}个分段")
    
    # 创建螺纹mesh
    bm = bmesh.new()
    
    # 生成螺纹螺旋线
    vertices_inner = []  # 内径螺旋线
    vertices_outer = []  # 外径螺旋线
    
    for i in range(total_segments + 1):
        t = i / segments_per_turn
        angle = t * 2 * math.pi
        z = t * pitch - thickness/2
        
        # 限制Z范围
        if z > thickness/2:
            z = thickness/2
        if z < -thickness/2:
            z = -thickness/2
            
        # 内径点（螺纹根部）
        x_inner = inner_radius * math.cos(angle)
        y_inner = inner_radius * math.sin(angle)
        vertices_inner.append((x_inner, y_inner, z))
        
        # 外径点（螺纹顶部）
        x_outer = outer_radius * math.cos(angle)
        y_outer = outer_radius * math.sin(angle)
        vertices_outer.append((x_outer, y_outer, z))
    
    # 将顶点添加到bmesh
    vert_inner_indices = []
    vert_outer_indices = []
    
    for v in vertices_inner:
        vert = bm.verts.new(v)
        vert_inner_indices.append(vert.index)
    
    for v in vertices_outer:
        vert = bm.verts.new(v)
        vert_outer_indices.append(vert.index)
    
    bm.verts.ensure_lookup_table()
    
    # 创建螺纹的四边形面
    for i in range(len(vert_inner_indices) - 1):
        try:
            inner_curr = vert_inner_indices[i]
            inner_next = vert_inner_indices[i + 1]
            outer_curr = vert_outer_indices[i]
            outer_next = vert_outer_indices[i + 1]
            
            # 创建四边形面
            face = bm.faces.new([
                bm.verts[inner_curr],
                bm.verts[inner_next],
                bm.verts[outer_next],
                bm.verts[outer_curr]
            ])
        except ValueError:
            pass  # 忽略无效面
    
    # 封闭螺纹两端
    # 顶端环
    top_inner = []
    top_outer = []
    bottom_inner = []
    bottom_outer = []
    
    # 找到顶端和底端的顶点
    for i, v_inner in enumerate(vertices_inner):
        if abs(v_inner[2] - thickness/2) < 0.01:  # 顶端
            top_inner.append(vert_inner_indices[i])
            top_outer.append(vert_outer_indices[i])
        elif abs(v_inner[2] + thickness/2) < 0.01:  # 底端
            bottom_inner.append(vert_inner_indices[i])
            bottom_outer.append(vert_outer_indices[i])
    
    # 创建环形面（简化版，连接内外径）
    if len(top_inner) >= 2 and len(top_outer) >= 2:
        for i in range(len(top_inner) - 1):
            try:
                face = bm.faces.new([
                    bm.verts[top_inner[i]],
                    bm.verts[top_outer[i]],
                    bm.verts[top_outer[i+1]],
                    bm.verts[top_inner[i+1]]
                ])
            except:
                pass
    
    if len(bottom_inner) >= 2 and len(bottom_outer) >= 2:
        for i in range(len(bottom_inner) - 1):
            try:
                face = bm.faces.new([
                    bm.verts[bottom_inner[i]],
                    bm.verts[bottom_inner[i+1]],
                    bm.verts[bottom_outer[i+1]],
                    bm.verts[bottom_outer[i]]
                ])
            except:
                pass
    
    # 更新法线
    bm.normal_update()
    bm.faces.ensure_lookup_table()
    
    # 创建螺纹mesh对象
    thread_mesh = bpy.data.meshes.new("CS_InternalThreads")
    bm.to_mesh(thread_mesh)
    bm.free()
    
    thread_obj = bpy.data.objects.new("InternalThreads", thread_mesh)
    bpy.context.collection.objects.link(thread_obj)
    
    # 将螺纹合并到主体（加法运算）
    bpy.ops.object.select_all(action='DESELECT')
    main_obj.select_set(True)
    thread_obj.select_set(True)
    bpy.context.view_layer.objects.active = main_obj
    bpy.ops.object.join()
    
    print("螺纹添加完成")

def add_material():
    """添加材质"""
    obj = bpy.context.active_object
    if obj:
        bpy.ops.object.shade_smooth()
        
        # 创建材质
        mat = bpy.data.materials.new(name="CS_Ring_Material")
        mat.use_nodes = True
        mat.node_tree.nodes.clear()
        
        bsdf = mat.node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
        bsdf.inputs['Base Color'].default_value = (0.7, 0.7, 0.7, 1.0)
        bsdf.inputs['Metallic'].default_value = 0.8
        bsdf.inputs['Roughness'].default_value = 0.2
        
        output = mat.node_tree.nodes.new(type='ShaderNodeOutputMaterial')
        mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
        
        obj.data.materials.append(mat)

def setup_viewport():
    """设置视口显示"""
    # 简化版本，只设置着色模式
    try:
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'SOLID'
                        space.shading.show_xray = True  # 透视模式，能看到内部结构
                        # 尝试调整视图
                        try:
                            with bpy.context.temp_override(area=area, region=area.regions[-1]):
                                bpy.ops.view3d.view_all()
                        except:
                            print("视图调整跳过（正常情况）")
                        break
    except Exception as e:
        print(f"视口设置跳过: {e}")
        pass

def export_stl(filename="cs_extension_ring_hollow_threaded.stl"):
    """导出STL文件"""
    if bpy.context.active_object:
        blend_path = bpy.data.filepath
        if blend_path:
            export_dir = os.path.dirname(blend_path)
        else:
            export_dir = os.path.expanduser("~/Desktop")
        
        export_path = os.path.join(export_dir, filename)
        
        # 确保对象被选中
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.active_object.select_set(True)
        
        bpy.ops.export_mesh.stl(
            filepath=export_path,
            use_selection=True,
            ascii=False,
            use_mesh_modifiers=True
        )
        
        print(f"STL文件已导出: {export_path}")
        return export_path
    return None

def main():
    """主函数"""
    print("=" * 70)
    print("🔧 创建CS转接环 - 空心带螺纹版本")
    print("=" * 70)
    print("📏 规格:")
    print("   • 内径: 25.4mm (带内螺纹)")
    print("   • 外径: 30.0mm") 
    print("   • 厚度: 3.0mm")
    print("   • 结构: 空心环形，内壁带螺纹")
    print("=" * 70)
    
    # 清除场景
    clear_scene()
    
    # 创建空心转接环
    extension_ring = create_cs_extension_ring()
    
    # 添加材质
    add_material()
    
    # 设置视口（透视模式查看内部）
    setup_viewport()
    
    # 导出STL
    export_path = export_stl("cs_extension_ring_hollow_with_threads.stl")
    
    if export_path:
        print("✅ 空心CS转接环创建成功!")
        print(f"📁 STL文件: {export_path}")
        print("")
        print("🔍 检查要点:")
        print("   • 中心应该是空心的")
        print("   • 内壁应该有螺纹结构")
        print("   • 两端开口，可以看穿")
        print("")
        print("💡 使用Blender查看:")
        print("   • 开启X-Ray模式可以看到内部螺纹")
        print("   • 使用剖面视图检查内部结构")
        print("=" * 70)
    else:
        print("❌ 导出失败")

# 执行
if __name__ == "__main__":
    main()
