from psychopy import visual


class StopStimulus(object):

    def __init__(self, screen, direction=0, arrow_size_horizontal_degrees=4):
        self.screen = screen
        self.direction = direction
        self.arrow_size_horizontal_degrees = arrow_size_horizontal_degrees

        if self.direction == 0:
            # Left stimulus
            vertices = [(0.2, 0.05),
                        (0.2, -0.05),
                        (0.0, -0.05),
                        (0, -0.1),
                        (-0.2, 0),
                        (0, 0.1),
                        (0, 0.05)]
        else:
            # right stimulus
            vertices = [(-0.2, 0.05),
                        (-0.2, -0.05),
                        (-.0, -0.05),
                        (0, -0.1),
                        (0.2, 0),
                        (0, 0.1),
                        (0, 0.05)]

        self.arrow = visual.ShapeStim(win=self.screen, vertices=vertices, fillColor='white',
                                      size=arrow_size_horizontal_degrees, lineColor='white',
                                      units='deg',
                                      lineColorSpace='rgb', fillColorSpace='rgb')

    def draw(self):
        self.arrow.draw()


class FixationCircle(object):

    def __init__(self, screen, circle_radius_degrees=4, line_width=1.5, line_color='white'):
        self.screen = screen
        self.circle_size_degrees = circle_radius_degrees

        self.circle_stim = visual.Circle(win=self.screen,
                                         radius=circle_radius_degrees, edges=50, lineWidth=line_width,
                                         lineColor=line_color, units='deg',
                                         lineColorSpace='rgb', fillColorSpace='rgb')

    def draw(self):
        self.circle_stim.draw()
