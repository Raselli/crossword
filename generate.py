import sys

from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        _, _, w, h = draw.textbbox((0, 0), letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        for value, words in self.domains.items():
            self.domains[value] = {
                word for word in words if len(word) == value.length
            }
        
    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        
        # Check for the existence of overlapping words
        overlap = self.crossword.overlaps[x, y]
        if overlap:
            valid_words = {
                word_x for word_x in self.domains[x]
                if any(
                    word_x[overlap[0]] == word_y[overlap[1]]
                    for word_y in self.domains[y]
                )
            }  
            
            # Update values of x
            if self.domains[x] != valid_words:       
                self.domains[x] = valid_words 
                return True
            
        return False

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        if not arcs:
            arcs = [
                (x, y) for x in self.domains for y in self.domains if x != y
            ]
            
        # Update self.domains
        while arcs:
            x, y = arcs.pop()
            if self.revise(x, y) and not self.domains[x]:
                return False
            for z in self.crossword.neighbors(x) - {y}:
                arcs.insert(0, (z, x))
                
        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        return set(assignment.keys()) == set(self.domains.keys())

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        
        # Words fit on the board
        words_fit_board = all(
            len(word[1]) == word[0].length for word in assignment.items()
        )      
          
        # No repeated words
        repetition = len(assignment.values()) == len(set(assignment.values()))

        # Words do not conflict with neighbours
        words_no_conflict = all(
            assignment[neighbour][self.crossword.overlaps[neighbour, word][0]]
            == assignment[word][self.crossword.overlaps[neighbour, word][1]]            
            for word in assignment.keys()
            for neighbour in self.crossword.neighbors(word)
            if neighbour in assignment 
        )

        # Return the 3 consistency-checks
        return all((repetition, words_fit_board, words_no_conflict))

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """

        # Comparing var's word-overlap with its neighbours
        rule_out_per_word = {
            word: sum(
                1 for neighbour in self.crossword.neighbors(var)
                if neighbour not in assignment
                for neighbour_word in self.domains[neighbour]
                if neighbour_word[self.crossword.overlaps[neighbour, var][0]]
                != word[self.crossword.overlaps[neighbour, var][1]]
            )
            for word in self.domains[var]
        }
        return sorted(rule_out_per_word, key=rule_out_per_word.get)

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """

        # Returns max. nested-tuple; (variable, (words, degree))
        return max((
            (
                domain[0], 
                (-len(domain[1]), len(self.crossword.neighbors(domain[0])))
            )
            for domain in self.domains.items() if domain[0] not in assignment
        ), key=lambda x: x[1])[0]    
               
    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """

        # Return complete assignement
        if self.assignment_complete(assignment):
            return assignment

        # Backtrack to complete assignement
        # No inference: Additional method-calls made it slower
        unassigned_var = self.select_unassigned_variable(assignment)
        for value in self.order_domain_values(unassigned_var, assignment):         
            assignment[unassigned_var] = value             
            if self.consistent(assignment):
                result = self.backtrack(assignment)
                if result:
                    return result
                del assignment[unassigned_var]
                
        # No solution
        return None

def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
