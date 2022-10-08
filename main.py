import math
import time
from PIL import Image, ImageDraw


# Static method container for vector methods (represented by lists/tuples)
class Vector:
    @staticmethod
    def normalize(vec):
        length = Vector.length(vec)
        return [component / length for component in vec]

    @staticmethod
    def add(vec1, vec2):
        return [vec1[i] + vec2[i] for i in range(3)]

    @staticmethod
    def sub(vec1, vec2):
        return [vec1[i] - vec2[i] for i in range(3)]

    @staticmethod
    def multiply(vec1, vec2):
        return [vec1[i] * vec2[i] for i in range(3)]

    @staticmethod
    def scale(vec, x):
        return [component * x for component in vec]

    @staticmethod
    def length(vec):
        return (vec[0] * vec[0] + vec[1] * vec[1] + vec[2] * vec[2]) ** (1 / 2)

    @staticmethod
    def dot(vec1, vec2):
        return sum(Vector.multiply(vec1, vec2))


# Base class for objects in a scene
class SpatialObject:
    # origin: the global position of the object
    # rotation: currently unused
    # specular: [0, inf], the amount that the dot product between light direction and surface normal affects brightness
    # reflectivity: [0, 1], the amount of light reflected at each collision
    def __init__(self, origin=None, rotation=None, color=(0, 0, 0), specular=1.5, reflectivity=0.8):
        if origin is None:
            origin = [0, 0, 0]
        if rotation is None:
            rotation = [0, 0, 0]
        self.origin = origin
        self.rotation = rotation
        self.color = color
        self.reflectivity = reflectivity
        self.specular = specular

    # Returns a tuple of (intersection point, ray bounce direction) if the ray intersects this object, else None
    def get_intersection(self, ray_dir, ray_origin):
        return None

    # Returns the normal of the surface at the point
    def get_normal(self, point):
        return None


# Casts rays onto a scene to render objects
class Camera(SpatialObject):
    # canvas_offset: how far the viewing plane is from the camera origin
    # canvas_size: a tuple of (width, height) in pixels of the screen
    # fov: field of view in radians
    def __init__(self, canvas_offset=0.5, canvas_size=None, fov=2.0944, *args, **kw):
        super().__init__(*args, **kw)
        if canvas_size is None:
            canvas_size = (300, 200)
        self.canvas_offset = canvas_offset
        self.canvas_size = canvas_size
        self.fov = fov
        self.max_bounces = 5

    # Renders the scene composed of the objects and lights variables onto the canvas image
    # canvas: a PIL Image to draw to
    # objects: a list of SpatialObjects to draw
    # lights: a list of Lights to apply to the objects
    def render(self, canvas, objects, lights):
        view_plane_width = 2 * math.tan(self.fov / 2) * self.canvas_offset
        view_plane_height = view_plane_width * self.canvas_size[1] / self.canvas_size[0]

        for row in range(self.canvas_size[1]):
            for col in range(self.canvas_size[0]):
                # Get the point that the ray intersects with the viewing plane
                px_x = (col / self.canvas_size[0]) * view_plane_width - (view_plane_width / 2)
                px_y = (row / self.canvas_size[1]) * view_plane_height - (view_plane_height / 2)
                px_z = self.canvas_offset

                ray_origin = self.origin
                ray_dir = Vector.normalize([px_x, px_y, px_z])

                # Keep track of the colors that the traced ray intersects with, along with the energy of the ray
                reflected_colors = []
                energy = 1.0
                for bounce in range(self.max_bounces):
                    # Get all intersections of this ray to other objects
                    intersections = []
                    for spatial_obj in objects:
                        intersect = spatial_obj.get_intersection(ray_dir, ray_origin)
                        if intersect is not None:
                            intersections.append(intersect + [spatial_obj])
                    if len(intersections) == 0:
                        continue

                    # Use only the closest intersection to the ray origin point
                    near_intersect = min(intersections, key=lambda z: Vector.length(Vector.sub(ray_origin, z[0])))

                    point_color = [0, 0, 0]
                    for light in lights:
                        to_light = Vector.sub(light.origin, near_intersect[0])

                        # Skip lights that are too far
                        if Vector.length(to_light) > light.max_distance:
                            continue

                        # Go through all other objects and check if there is a clear path from the light to the point
                        blocked = False
                        for shadow_obj in objects:
                            if shadow_obj.get_intersection(Vector.normalize(to_light), near_intersect[0]) is not None:
                                blocked = True
                                break
                        if blocked:
                            continue

                        # Get the dot product of the surface normal and the light (more similar = stronger)
                        normal = near_intersect[2].get_normal(near_intersect[0])
                        similarity = ((Vector.dot(Vector.normalize(to_light), normal) / 2) + 0.5)
                        similarity **= near_intersect[2].specular

                        # Get the distance from the light (closer = stronger)
                        distance_ratio = Vector.length(to_light) / light.max_distance

                        # Calculate the strength from distance, similarity, and the light's current energy
                        strength = ((1 - distance_ratio) ** light.power) * similarity * energy

                        point_color = Vector.add(point_color, Vector.multiply(near_intersect[2].color,
                                                                              Vector.scale(light.color, strength)))
                    # Update the next point and save the color
                    reflected_colors.append(point_color)
                    ray_origin = near_intersect[0]
                    ray_dir = near_intersect[1]

                    # Weaken the reflected ray
                    energy *= near_intersect[2].reflectivity

                # Average all the colors encountered in the bounces
                r = min(255, int(255 * sum(c[0] for c in reflected_colors) / self.max_bounces))
                g = min(255, int(255 * sum(c[1] for c in reflected_colors) / self.max_bounces))
                b = min(255, int(255 * sum(c[2] for c in reflected_colors) / self.max_bounces))

                canvas.point((col, row), (r, g, b))


# Stores information of a light for a scene
class Light(SpatialObject):
    def __init__(self, max_distance=1, power=0.8, *args, **kw):
        super().__init__(*args, **kw)
        self.max_distance = max_distance
        self.power = power


# A flat plane object that is always facing up
class Floor(SpatialObject):
    def get_intersection(self, ray_dir, ray_origin):
        if Vector.dot(ray_dir, (0, 1, 0)) <= 0:
            return None
        dif_y = self.origin[1] - ray_origin[1]
        dif_x = (dif_y / ray_dir[1]) * ray_dir[0]
        dif_z = (dif_y / ray_dir[1]) * ray_dir[2]

        p1 = Vector.add(ray_origin, [dif_x, dif_y, dif_z])
        # We never recalculate the normal because we assume this plane does not rotate
        reflect_dir = Vector.sub(ray_dir, Vector.scale([0, -1, 0], Vector.dot(ray_dir, [0, -1, 0]) * 2))

        # Leave out reflection direction to make the floor look flat
        return [p1, reflect_dir]

    def get_normal(self, point):
        return [0, -1, 0]


class Sphere(SpatialObject):
    def __init__(self, radius=1, *args, **kw):
        super().__init__(*args, **kw)
        self.radius = radius

    def get_intersection(self, ray_dir, ray_origin):
        # Get the length of the vector from the ray point to the center of the sphere
        a = Vector.sub(self.origin, ray_origin)
        # Get the length of the vector that goes along the ray until a point that forms a right triangle with a
        b = Vector.dot(a, ray_dir)

        # If the length is negative, the ray is opposite the direction of the sphere
        if b < 0:
            return None

        # Get the length of the side that creates a right triangle between a and b
        c = (Vector.length(a) ** 2 - b ** 2) ** 0.5

        # If larger than the sphere, the ray never intersected with the sphere
        if c > self.radius:
            return None

        # Get the distance from the ray origin to the ray intersection
        d = b - (self.radius - c) ** 0.5

        # Find the point by tracing the ray and then reflect it using the normal
        p = Vector.add(ray_origin, Vector.scale(ray_dir, d))
        normal = self.get_normal(p)
        reflect_dir = Vector.sub(ray_dir, Vector.scale(normal, Vector.dot(ray_dir, normal) * 2))

        return [p, reflect_dir]

    def get_normal(self, point):
        return Vector.normalize(Vector.sub(point, self.origin))


def main():
    width = 800
    height = 600

    # Initializing the scene
    cam = Camera(canvas_size=[width, height], origin=[0, 1, 0])
    a = Sphere(origin=[0, 4, 32], radius=8, reflectivity=0.6, specular=2, color=(0.858, 0.858, 0.858))
    b = Sphere(origin=[-12, 2, 24], radius=4, reflectivity=0.1, color=(0.501, 0.501, 0.501))
    c = Sphere(origin=[-18, 8, 18], radius=4, specular=1.0, color=(0.12, 0.12, 0.12))
    d = Sphere(origin=[19, -4, 22], radius=5, specular=1.2, reflectivity=2, color=(0.1, 0.1, 0.1))
    e = Sphere(origin=[16, 8, 18], radius=5, specular=1.0, reflectivity=1.0, color=(1.0, 1.0, 1.0))
    f = Floor(origin=[0, 16, 0], reflectivity=0.32, color=(0.5, 0.5, 0.5))

    light1 = Light(origin=[24, -8, 8], power=1.0, color=(16.0, 16.0, 16.0), max_distance=50)
    light2 = Light(origin=[0, -16, 32], power=1.0, color=(2.0, 0.8, 0.8), max_distance=64)
    light3 = Light(origin=[-16, -22, 24], power=1.0, color=(1.0, 0.8, 2.0), max_distance=64)

    # Set up PIL to render the image
    im = Image.new(mode="RGB", size=cam.canvas_size)
    draw = ImageDraw.Draw(im)

    start = time.time()
    cam.render(draw, [a, b, c, d, f, e], [light1, light2, light3])
    print("Rendering complete: %f seconds" % (time.time() - start))

    with open("render.png", "wb") as f:
        im.save(f)


if __name__ == "__main__":
    main()
