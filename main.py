import os
import sys
import random
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    GeoMipTerrain, Texture, TextureStage, DirectionalLight, AmbientLight,
    NodePath, PandaNode, WindowProperties, Vec3, Point3, BitMask32,
    CardMaker
)
from panda3d.bullet import (
    BulletWorld, BulletPlaneShape, BulletRigidBodyNode, BulletCapsuleShape,
    BulletDebugNode, BulletTriangleMesh, BulletTriangleMeshShape, ZUp,
    BulletBoxShape, BulletGhostNode, BulletSphereShape
)
from perlin_noise import PerlinNoise
from PIL import Image

class PlayerController:
    def __init__(self, camera, win, physics_world):
        self.camera = camera
        self.win = win
        self.physics_world = physics_world
        height = 1.7
        radius = 0.4
        shape = BulletCapsuleShape(radius, height - 2 * radius, ZUp)
        self.player_node = BulletRigidBodyNode('Player')
        self.player_node.set_mass(1.0)
        self.player_node.add_shape(shape)
        self.player_node.set_angular_factor(Vec3(0))
        self.player_node.set_friction(0.7)
        self.player_node.set_linear_sleep_threshold(0)
        self.player_node.set_angular_sleep_threshold(0)
        self.player_np = base.render.attach_new_node(self.player_node)
        self.physics_world.attach_rigid_body(self.player_node)
        self.camera.reparent_to(self.player_np)
        self.camera.set_pos(0, 0, height / 2)
        self.speed = 10.0
        self.rotation_speed = 80.0
        self.heading = 0
        self.pitch = 0
        self.keys = {"forward": False, "backward": False, "left": False, "right": False}
        self.setup_input()
        base.task_mgr.add(self.update, "player_update_task")

    def setup_input(self):
        base.accept("w", self.set_key, ["forward", True])
        base.accept("w-up", self.set_key, ["forward", False])
        base.accept("s", self.set_key, ["backward", True])
        base.accept("s-up", self.set_key, ["backward", False])
        base.accept("a", self.set_key, ["left", True])
        base.accept("a-up", self.set_key, ["left", False])
        base.accept("d", self.set_key, ["right", True])
        base.accept("d-up", self.set_key, ["right", False])
        props = WindowProperties()
        props.set_cursor_hidden(True)
        props.set_mouse_mode(WindowProperties.M_RELATIVE)
        self.win.request_properties(props)

    def set_key(self, key, value):
        self.keys[key] = value

    def update(self, task):
        dt = globalClock.get_dt()
        md = self.win.get_pointer(0)
        delta_x, delta_y = md.get_x(), md.get_y()
        self.heading -= delta_x * self.rotation_speed * dt * 0.1
        self.pitch = max(-80, min(80, self.pitch - delta_y * self.rotation_speed * dt * 0.1))
        self.player_np.set_h(self.heading)
        self.camera.set_p(self.pitch)
        move_vec = Vec3(0, 0, 0)
        if self.keys["forward"]: move_vec.set_y(1)
        if self.keys["backward"]: move_vec.set_y(-1)
        if self.keys["left"]: move_vec.set_x(-1)
        if self.keys["right"]: move_vec.set_x(1)
        if move_vec.length_squared() > 0:
            move_vec.normalize()
        rotated_move_vec = self.player_np.get_quat().xform(move_vec)
        rotated_move_vec.z = 0
        current_vel = self.player_node.get_linear_velocity()
        new_vel = rotated_move_vec * self.speed
        new_vel.z = current_vel.z
        self.player_node.set_linear_velocity(new_vel)
        self.player_node.set_active(True)
        return task.cont

    def set_pos(self, pos):
        self.player_node.set_linear_velocity(Vec3(0))
        self.player_node.set_angular_velocity(Vec3(0))
        self.player_np.set_pos(pos)

class MyApp(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.disable_mouse()
        self.terrain_size = 513
        self.terrain_root = None
        self.artifacts = []
        self.trees = []
        self.terrain_phys_node = None

        self.setup_physics()
        self.regenerate_world(is_initial=True)
        self.setup_lighting()
        self.player_controller = PlayerController(self.camera, self.win, self.physics_world)

        # Set initial player position after first world gen
        spawn_pos = self.find_valid_spawn_point() or Point3(0, 0, 50)
        self.player_controller.set_pos(spawn_pos)

        self.toggle_debug()

    def setup_physics(self):
        self.physics_world = BulletWorld()
        self.physics_world.set_gravity(Vec3(0, 0, -9.81))
        base.task_mgr.add(self.update_physics, "update_physics")

    def update_physics(self, task):
        dt = globalClock.get_dt()
        self.physics_world.do_physics(dt)
        self.check_artifact_triggers()
        return task.cont

    def clear_world(self):
        # Clear artifacts
        for ghost_node in self.artifacts:
            self.physics_world.remove_ghost(ghost_node)
        self.artifacts.clear()
        for np in self.render.find_all_matches("**/artifact_visual"):
            np.remove_node()

        # Clear trees
        for tree_phys_node, tree_visual_np in self.trees:
            self.physics_world.remove_rigid_body(tree_phys_node)
            tree_visual_np.remove_node()
        self.trees.clear()

        # Clear terrain
        if self.terrain_phys_node:
            self.physics_world.remove_rigid_body(self.terrain_phys_node)
            self.terrain_phys_node = None
        if self.terrain_root:
            self.terrain_root.remove_node()
            self.terrain_root = None

    def regenerate_world(self, is_initial=False):
        print("Generating new world...")
        self.clear_world()
        self.create_terrain()
        self.place_objects(num_trees=50, num_artifacts=5)
        if not is_initial:
            spawn_pos = self.find_valid_spawn_point() or Point3(0, 0, 50)
            self.player_controller.set_pos(spawn_pos)
        print("World generation complete.")

    def create_terrain(self):
        seed = random.randint(0, 10000)
        noise = PerlinNoise(octaves=4, seed=seed)
        pic = [[noise([i/self.terrain_size, j/self.terrain_size]) for j in range(self.terrain_size)] for i in range(self.terrain_size)]
        min_val, max_val = min(min(row) for row in pic), max(max(row) for row in pic)
        img_data = [int(((v - min_val) / (max_val - min_val)) * 255) for r in pic for v in r]

        image = Image.new('L', (self.terrain_size, self.terrain_size))
        image.putdata(img_data)
        image.save("heightmap.png")

        terrain = GeoMipTerrain("my_terrain")
        terrain.set_heightfield("heightmap.png")
        terrain.set_block_size(32)

        self.terrain_root = terrain.get_root()
        self.terrain_root.reparent_to(self.render)
        self.terrain_root.set_sz(100)
        center_offset = (self.terrain_size - 1) / 2
        self.terrain_root.set_pos(-center_offset, -center_offset, 0)
        terrain.generate()

        mesh = BulletTriangleMesh()
        for geom_node in self.terrain_root.find_all_matches('**/+GeomNode'):
            for geom in geom_node.node().get_geoms():
                mesh.add_geom(geom)

        shape = BulletTriangleMeshShape(mesh, dynamic=False)
        self.terrain_phys_node = BulletRigidBodyNode('Terrain')
        self.terrain_phys_node.add_shape(shape)
        self.render.attach_new_node(self.terrain_phys_node)
        self.physics_world.attach_rigid_body(self.terrain_phys_node)

    def place_objects(self, num_trees, num_artifacts):
        cm = CardMaker('card')
        cm.set_frame(-0.5, 0.5, -0.5, 0.5)
        box_model = NodePath('box')
        for i in range(6):
            face = box_model.attach_new_node(cm.generate())
            if i == 0: face.set_pos(0, -0.5, 0)
            elif i == 1: face.set_hpr(180, 0, 0); face.set_pos(0, 0.5, 0)
            elif i == 2: face.set_hpr(0, -90, 0); face.set_pos(0, 0, 0.5)
            elif i == 3: face.set_hpr(0, 90, 0); face.set_pos(0, 0, -0.5)
            elif i == 4: face.set_hpr(-90, 0, 0); face.set_pos(0.5, 0, 0)
            elif i == 5: face.set_hpr(90, 0, 0); face.set_pos(-0.5, 0, 0)
        box_model.flatten_strong()

        for _ in range(num_trees):
            pos = self.find_valid_spawn_point()
            if pos:
                tree_np = self.render.attach_new_node("tree_visual")
                box_model.instance_to(tree_np)
                tree_np.set_pos(pos)
                tree_np.set_scale(1, 1, random.uniform(3.0, 6.0))
                shape = BulletBoxShape(Vec3(0.5, 0.5, tree_np.get_sz().z / 2))
                node = BulletRigidBodyNode('Tree')
                node.add_shape(shape)
                np = self.render.attach_new_node(node)
                np.set_pos(pos + Vec3(0, 0, tree_np.get_sz().z / 2))
                self.physics_world.attach_rigid_body(node)
                self.trees.append((node, tree_np))

        for _ in range(num_artifacts):
            pos = self.find_valid_spawn_point()
            if pos:
                artifact_np = self.render.attach_new_node("artifact_visual")
                box_model.instance_to(artifact_np)
                artifact_np.set_pos(pos + Vec3(0,0,1))
                artifact_np.set_color(1, 0, 0, 1)
                shape = BulletSphereShape(radius=1.5)
                ghost_node = BulletGhostNode('Artifact')
                ghost_node.add_shape(shape)
                ghost_np = self.render.attach_new_node(ghost_node)
                ghost_np.set_pos(pos + Vec3(0,0,1))
                self.physics_world.attach_ghost(ghost_node)
                self.artifacts.append(ghost_node)

    def find_valid_spawn_point(self):
        max_tries = 50
        for _ in range(max_tries):
            terrain_w = (self.terrain_size - 1)
            x = random.uniform(-terrain_w / 2, terrain_w / 2)
            y = random.uniform(-terrain_w / 2, terrain_w / 2)
            p_from = Point3(x, y, 1000)
            p_to = Point3(x, y, -1000)
            result = self.physics_world.ray_test_closest(p_from, p_to)
            if result.has_hit() and result.get_node().name == 'Terrain':
                if result.get_hit_normal().z > 0.85:
                    return result.get_hit_pos() + Point3(0,0,1)
        return None

    def check_artifact_triggers(self):
        for ghost_node in self.artifacts:
            if ghost_node.get_overlapping_nodes():
                if any(node.name == 'Player' for node in ghost_node.get_overlapping_nodes()):
                    print("Player touched an artifact! Teleporting...")
                    self.regenerate_world()
                    return

    def setup_lighting(self):
        alight = AmbientLight('alight')
        alight.set_color((0.2, 0.2, 0.2, 1))
        alnp = self.render.attach_new_node(alight)
        self.render.set_light(alnp)
        dlight = DirectionalLight('dlight')
        dlight.set_color((0.8, 0.8, 0.7, 1))
        dlnp = self.render.attach_new_node(dlight)
        dlnp.set_hpr(0, -60, 0)
        self.render.set_light(dlnp)

    def toggle_debug(self):
        if not hasattr(self, 'debug_np'):
            self.debug_np = self.render.attach_new_node(BulletDebugNode('Debug'))
            self.physics_world.set_debug_node(self.debug_np.node())
            self.accept('f1', self.toggle_debug)
        if self.debug_np.is_hidden():
            self.debug_np.show()
        else:
            self.debug_np.hide()

app = MyApp()
app.run()
