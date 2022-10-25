"""File: three_shapes_game.py

   Author: Russ Lewis

   Purpose: Defines the Game class, which provides the core mechanisms for the
            Three Shapes family of programs.
"""


import math        # for sqrt

from graphics import graphics



class Game:
    def __init__(self, title, frame_rate, wid,hei):
        """Constructor.  Initializes the game to have zero objets; call
           add_obj() to add objects to the system.

           Parameters: the width and height of the window
        """
        self._wid = wid
        self._hei = hei

        self._frame_rate = frame_rate

        self._win = graphics(wid,hei, title)

        # this is a configuration setting - it changes how we calculate
        # the distance between objects in do_nearby_calls()
        self._account_for_radii_in_dist = False

        # the user must call add_obj() to add to this set
        self._active_objs = set()

        # see what remove_obj() and perform_moves() do, to understand this
        # variable.
        self._pending_removes = set()
        self._pending_adds    = set()

        # I plan to add a feature, where the user can mark the game as "over"
        self._game_over = False



    def config_set(self, param, val):
        """Function to set various config variables.  Right now, it only
           supports a single parameter; I might add more later.  Give the name
           of the parameter (as a string), then the value.

           Parmeters: config parameter to set, value

           Supported Config Options:
             "account_for_radii_in_dist" -> Boolean
        """
        if param == "account_for_radii_in_dist":
            self._account_for_radii_in_dist = val
        else:
            assert False   # unrecognized config parameter



    def set_game_over(self):
        self._game_over = True
    def is_over(self):
        return self._game_over



    # ADD / REMOVE LOGIC
    #
    # In the do_nearby_calls() and do_move_calls() methods, we loop over
    # lots of objects.  Inside those methods, the user may choose to call
    # remove_obj(); if they do, then ideally we would just remove it
    # immediately.  But we're in the middle of a loop: what if we call
    # nearby() or move() on a recently-removed object, or if we pass it as
    # a parameter to a nearby() call?
    #
    # Similarly, the user might call add_obj() at almost any time; most
    # programs will call it at the top of the game loop, but you could also
    # imagine a "spawn when touching" program, which would create new objects
    # inside the nearby() move (or just about anything else).
    #
    # So, how do we handle adds and removes that happen while the loops are
    # already running?
    #
    # One option would be to force the remove logic to exclude such objects
    # from the loop as it runs, but that's not the easiest thing in the
    # world.  Instead, remove_obj() will add an object to a set of "pending
    # removes" - none of these removals will take place until the game loop
    # calls execute_removes() - which happens *after* all of the nearby()
    # and move() calls have finished.
    #
    # Similarly, a new object can be added at any time, but it will not
    # actually take place until a few moments later.
    #
    # The actual adds and removes will take place at the *top* of the draw()
    # methods.  We will do this by calling the _execute_adds_and_removes()
    # helper.
    #
    # NOTE:
    # When the user calls remove_obj(), it *MUST* be in the current set of
    # active objects.  It is *permissible* to call it multiple times in the
    # same game tick.

    def add_obj(self, new_obj):
        """Adds a new object to the game.  Can be called at any time, although
           if called in the middle of the nearby() or move() loops, it will not
           be added to the ongoing loop.  The object must implement the
           standard methods required of any object: get_xy(), get_radius(),
           nearby(), move(), and draw().

           Parameters: the new object
        """
        assert new_obj not in self._active_objs
        assert new_obj not in self._pending_adds
        self._pending_adds.add(new_obj)

    def remove_obj(self, bad_obj):
        """Queues up an object to be removed from the game.  It is
           permissible to call this multiple times on the same object during
           one clock tick; all of the removals will take place at once,
           *after* all of the nearby() and move() calls have been completed,
           but *before* any draw() calls.  It is illegal to call this if the
           object is not currently in the game.

           Arguments: object to remove
        """
        assert bad_obj in self._active_objs
        self._pending_removes.add(bad_obj)



    def _execute_adds_and_removes(self):
        """Helper function, used to handle common code in several of the
           primary game-loop functions.  Do not call directly.
        """
        self._active_objs -= self._pending_removes
        self._pending_removes = set()

        self._active_objs.update(self._pending_adds)
        self._pending_adds = set()



    def do_nearby_calls(self):
        """Figures out how close each object is to every other, sorts them by
           distance, and then performs all of the nearby() calls on the object
           pairs.  Makes all of the calls for a given "left-hand" object as a
           block; if the user returns False from any call, we terminate that
           inner loop, and then start delivering values for another left-hand
           value.

           Parameters: none
        """

        positions = []
        for o in self._active_objs:
            x,y = o.get_xy()
            positions.append( (o,x,y) )

        # Note that we're doing a 2D loop, but because we're only looking for
        # one version of each pair (not the reversed), notice that we do
        # something funny with the lower bound of the inner loop variable.
        distances = []
        for i in range(len(positions)):
            for j in range(i+1, len(positions)):
                o1,x1,y1 = positions[i]
                o2,x2,y2 = positions[j]

                dist = math.sqrt( (x1-x2)**2 + (y1-y2)**2 )

                if self._account_for_radii_in_dist:
                    dist -= o1.get_radius()
                    dist -= o2.get_radius()

                # we add two records to the 'distances' array, so that we can
                # simply *sort* that list at the end.  Note that the way that
                # we arrange this, we will organize first by the left-hand
                # object, then by the distance, and then by the right-hand
                # object (the last of which will rarely be an issue)
                #
                # UPDATE: Note that I wanted to use object references here -
                #         but then I realized that we couldn't sort by those!
                #         so I need to use the indices into the positions[]
                #         array instead.
                distances.append( (i,dist,j) )
                distances.append( (j,dist,i) )


        # now that we're done *creating* the distances, we can sort all of
        # them.
        distances.sort()


        # there should be exactly n(n-1) elements in the array - since every
        # object in the game will be paired with n-1 others.
        n = len(positions)
        assert len(distances) == n*(n-1)

        # this loop is weird - but we have n different objects, each of which
        # has n-1 partners.  So I will implement each inner loop as looping
        # over a slice of the distances array.
        for i in range(n):
            for entry in distances[ (n-1)*i : (n-1)*(i+1) ]:
                k1,dist,k2 = entry
                assert k1 == i

                left  = positions[k1][0]
                right = positions[k2][0]

                # if the user returns False, then we will terminate this as a
                # left-hand element.
                if not left.nearby(right, dist, self):
                    break



    def do_move_calls(self):
        """Calls move() on every object in the game"""
        for o in self._active_objs:
            o.move(self)



    def do_edge_calls(self):
        """Finds any objects that are close to any edge - defined as within the
           radius of it (that is, touching or overlapping) - and calls edge()
           on them.

           Parameters: none
        """

        for o in self._active_objs:
            x,y = o.get_xy()
            rad = o.get_radius()

            if x < rad:
                o.edge("left", 0)
            if y < rad:
                o.edge("top", 0)

            if x+rad >= self._wid:
                o.edge("right", self._wid)
            if y+rad >= self._hei:
                o.edge("bottom", self._hei)



    def draw(self):
        """Calls draw() on every object in the game.  Also does the rest of the
           misc calls necessary to animate the window.
        """

        # execute pending object changes (if any)
        self._execute_adds_and_removes()

        # if the window has been destroyed, then we will throw an exception when
        # we run clear() below.  So check for this condition first!
        if self._win.is_killed:
            self._game_over = True
            return

        self._win.clear()

        for o in self._active_objs:
            o.draw(self._win)

        self._win.update_frame(self._frame_rate)
