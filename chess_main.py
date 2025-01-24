import pygame as pg
import game_setup.chess_rule as chess_rule
from retard_engines import random_moves, one_move_thinker
from advaced_engines import simple_minimax
from AI_standard_setting import ai_default_setting

BOARD_WIDTH = BOARD_HEIGHT = 1024
MOVE_LOG_WIDTH = 250
MOVE_LOG_HEIGHT = BOARD_HEIGHT
SIZE = 8
SQUARE_SIZE = BOARD_WIDTH // SIZE
FPS = 120
IMAGES = {}
SOUND_EFFECT = {}
GRAVITY = 2.5
FRICTION = 0.01
DRAG_POS = 0.33


#load images of pieces given style
def load_images(style = "neo"):
    pieces = ['P', 'R', 'N', 'B', 'Q', 'K']
    colors = ['w', 'b']
    for color in colors:
        for piece in pieces:
            IMAGES[color + piece] = pg.transform.scale(pg.image.load("images/Pieces/" + style + "/" + color + piece + ".png"), (SQUARE_SIZE, SQUARE_SIZE))

#load the sound effects
def load_sound_effects():
    cases = ["move", "capture", "check", "castle"]
    for case in cases:
        SOUND_EFFECT[case] = pg.mixer.Sound("sound/" + case + ".mp3")
        SOUND_EFFECT[case].set_volume(0.5)

from chess_physical_pieces import PhysicalPiece

# main game loop
def main():
    pg.init()
    screen = pg.display.set_mode((BOARD_WIDTH + MOVE_LOG_WIDTH,BOARD_HEIGHT))
    clock = pg.time.Clock()
    screen.fill((47, 47, 47))
    move_log_font = pg.font.SysFont("Aptos Display", 28, False, False)
    white_is_human = False
    black_is_human = False

    #setup the game
    gp = chess_rule.GamePosition()
    legal_moves = gp.get_legal_moves()
    move_made = False
    click_animation = False
    drag_animation = False
    load_images()
    load_sound_effects()
    draw_game_position(screen, gp, legal_moves, (), move_log_font)

    #run the game
    running =True
    cur_sq = ()
    clicks = []
    game_over = False
    while running:
        human_turn =  (white_is_human and gp.white_turn) or (black_is_human and not gp.white_turn)
        for e in pg.event.get():
            if e.type == pg.QUIT:
                running = False   
            # mouse handlers
            elif e.type == pg.MOUSEBUTTONDOWN or e.type == pg.MOUSEBUTTONUP:
                if e.button == 1 and not game_over and human_turn:
                    loc = pg.mouse.get_pos()
                    col = loc[0] // SQUARE_SIZE
                    row = loc[1] // SQUARE_SIZE
                    if (cur_sq == () and e.type == pg.MOUSEBUTTONUP) or col >= 8: #reset when a square is clicked twice or the move log is clicked
                        cur_sq = ()
                        clicks =[]
                    else: #store the selected squares
                        cur_sq = (row, col)
                        clicks.append(cur_sq)
                    if ((len(clicks) == 1) or (len(clicks) == 2 and ((gp.position[clicks[0][0]][clicks[0][1]][0] == 'w') == gp.white_turn))) and e.type == pg.MOUSEBUTTONDOWN: #generate the physical piece when dragging
                        clicks = [cur_sq]
                        if gp.position[cur_sq[0]][cur_sq[1]] != '--':
                            loc = dragging_physical_piece(screen, gp, legal_moves, cur_sq, move_log_font, loc, clock)
                            col = loc[0] // SQUARE_SIZE
                            row = loc[1] // SQUARE_SIZE                           
                            if col >= 8:
                                cur_sq = ()
                                clicks = []
                            elif cur_sq != (row, col):
                                cur_sq = (row, col)
                                clicks.append(cur_sq)
                                drag_animation = True
                    if len(clicks) == 2: #when two different squares are selected, act the introduced move
                        move = chess_rule.Move(clicks[0], clicks[1], gp.position)
                        is_promotion = False
                        for i in range(len(legal_moves)):
                            if move == legal_moves[i]:                               
                                if legal_moves[i].is_promotion:
                                    is_promotion = True
                                    selected_promotion_piece = display_promotion_UI(screen, legal_moves[i], clock, drag_animation)
                                    legal_moves[i].promotion_piece = selected_promotion_piece
                                if (not legal_moves[i].is_promotion) or selected_promotion_piece != '?':
                                    legal_moves[i].check_rep(legal_moves)
                                    gp.make_move(legal_moves[i])                                
                                    click_animation = not drag_animation
                                    move_made = True
                                cur_sq = ()
                                clicks = []
                        if (not move_made) and (not is_promotion):
                            if e.type == pg.MOUSEBUTTONDOWN and not drag_animation:
                                clicks = [cur_sq]
                            else:
                                cur_sq = clicks[0]
                                clicks = [clicks[0]]

            # key handlers
            elif e.type == pg.KEYDOWN:
                if e.key == pg.K_LEFT: #undo a move when 'LEFT' is pressed
                    gp.undo_move()
                    if not white_is_human or not black_is_human:
                        gp.undo_move()
                    move_made = True
                    click_animation = False
                    drag_animation = False
                    game_over = False
                if e.key == pg.K_r: #reset the game when 'r' is pressed
                    gp = chess_rule.GamePosition()
                    legal_moves = gp.get_legal_moves()
                    cur_sq = ()
                    clicks = []
                    move_made = False
                    click_animation = False
                    drag_animation = False
                    game_over = False

        #let ai makes a move
        if not game_over and not human_turn:
            ai_default_setting.expand_promotions_of_moves(legal_moves, gp.position)
            if gp.white_turn:
                AI_move = simple_minimax.Nega_max_find_move(gp, legal_moves)
            else:
                AI_move = simple_minimax.Nega_max_find_move(gp, legal_moves)

            if AI_move != None:
                AI_move.check_rep(legal_moves)
                gp.make_move(AI_move)
                move_made = True
                click_animation = True

        if move_made:
            if click_animation:
                animate_click_move(gp.move_history[-1], screen, gp.position, clock)
            elif drag_animation:
                animate_drag_move(gp.move_history[-1], screen, gp.position, clock)
            legal_moves = gp.get_legal_moves()
            if len(gp.move_history) != 0:
                gp.move_history[-1].is_check = gp.in_check
                gp.move_history[-1].is_checkmate = gp.checkmate
                gp.move_history[-1].is_stalemate = gp.stalemate
                play_sound_effects(gp.move_history[-1])
            move_made = False
            click_animation = False
            drag_animation = False

        draw_game_position(screen, gp, legal_moves, cur_sq, move_log_font)

        if gp.checkmate:
            game_over = True
            if gp.white_turn:
                draw_end_text(screen, "Black wins by checkmate.")
            else:
                draw_end_text(screen, "White wins by checkmate.")
        elif gp.stalemate:
            game_over = True
            draw_end_text(screen, "Draw by stalemate.")


        clock.tick(FPS)
        pg.display.flip()
    pg.quit()



#drawing functions of the board:
#drawing all stationary stuff
def draw_game_position(screen, gp, legal_moves, active_sq, move_log_font, active_colors = [pg.Color("light sky blue"), pg.Color("dodger blue")]):
    global active_sq_colors
    active_sq_colors = active_colors
    draw_board(screen)
    draw_highlighted_squares(screen, gp, active_sq)
    draw_pieces(screen, gp.position)
    draw_legal_moves(screen, gp, active_sq, legal_moves)
    draw_move_log(screen, gp, move_log_font)

#drawing the highlighted squares
def draw_highlighted_squares(screen, gp, active_sq):
    global active_sq_colors
    if active_sq != ():
        r, c = active_sq
        if gp.position[r][c][0] == ('w' if gp.white_turn else 'b'):
            s = pg.Surface((SQUARE_SIZE,SQUARE_SIZE))
            #s.set_alpha(200)
            s.fill(pg.Color(active_sq_colors[(r + c) % 2]))
            screen.blit(s, (c*SQUARE_SIZE, r*SQUARE_SIZE))

    if len(gp.move_history) != 0:
        last_move = gp.move_history[-1]
        pg.draw.rect(screen, active_sq_colors[(last_move.start_col + last_move.start_row) % 2], pg.Rect(last_move.start_col*SQUARE_SIZE, last_move.start_row*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
        pg.draw.rect(screen, active_sq_colors[(last_move.end_col + last_move.end_row) % 2], pg.Rect(last_move.end_col*SQUARE_SIZE, last_move.end_row*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

#drawing the legal moves suggestion
def draw_legal_moves(screen, gp, active_sq, legal_moves, legal_move_dot_rad = (SQUARE_SIZE * 0.1), legal_move_color = "dark green"):
    if active_sq != ():
        r, c = active_sq
        if gp.position[r][c][0] == ('w' if gp.white_turn else 'b'):
            dot = pg.Surface((SQUARE_SIZE, SQUARE_SIZE))
            dot.set_colorkey((0,0,0))
            dot.set_alpha(0)
            pg.draw.circle(dot, pg.Color(legal_move_color), (SQUARE_SIZE // 2, SQUARE_SIZE // 2), legal_move_dot_rad)
            dot.set_alpha(200)
            for move in legal_moves:
                if move.start_row == r and move.start_col == c:
                    screen.blit(dot, (SQUARE_SIZE * move.end_col, SQUARE_SIZE * move.end_row))

#drawing the chessboard
def draw_board(screen, color = "steel blue"):
    global board_colors
    board_colors = [pg.Color("White"), pg.Color(color)]
    for r in range(SIZE):
        for c in range(SIZE):
            pg.draw.rect(screen, board_colors[(r+c) % 2], pg.Rect(r*SQUARE_SIZE, c*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

#drawing the pieces
def draw_pieces(screen, position):
    for r in range(SIZE):
        for c in range(SIZE):
            piece = position[c][r]
            if piece != '--':
                screen.blit(IMAGES[piece], pg.Rect(r*SQUARE_SIZE, c*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

#drawing the end text
def draw_end_text(screen, text):
    font = pg.font.SysFont("Times New Roman", 48, True, False)
    text_obj = font.render(text, 0, pg.Color("Black"))
    text_loc = pg.Rect(0, 0, BOARD_WIDTH, BOARD_HEIGHT).move(BOARD_WIDTH / 2 - text_obj.get_width() / 2, BOARD_HEIGHT / 2 - text_obj.get_height() / 2)
    screen.blit(text_obj, text_loc)

#write the move log
def draw_move_log(screen, gp, font):
    move_log_rect = pg.Rect(BOARD_WIDTH, 0, MOVE_LOG_WIDTH, MOVE_LOG_HEIGHT)
    pg.draw.rect(screen, (47, 47, 47), move_log_rect)
    move_log = gp.move_history
    move_texts = []
    for i in range(0, len(move_log)):
        move_str = str(move_log[i])
        move_texts.append(move_str)

    padding = 10
    line_spacing = 8
    text_y = padding
    text_obj = font.render("Moves", 0, pg.Color("silver"))
    text_loc = move_log_rect.move(MOVE_LOG_WIDTH / 2 - text_obj.get_width() / 2, text_y)
    screen.blit(text_obj, text_loc)
    text_y += (text_obj.get_height() + line_spacing)
    light_background_rect = pg.Rect(BOARD_WIDTH, 0, MOVE_LOG_WIDTH, text_obj.get_height() + line_spacing)
    for i in range(len(move_texts)):
        if i % 4 == 2:
            pg.draw.rect(screen, (75,75,75), light_background_rect.move(0, text_y - line_spacing // 2))
        text = move_texts[i]
        text_obj = font.render(text, 0, pg.Color("silver"))
        if i % 2 == 0:
            turn_str = ('  ' if (i // 2 + 1 <= 9) else '') + str(i // 2 + 1) + '.'
            turn_obj = font.render(turn_str, 0, pg.Color("silver"))
            turn_str_loc = move_log_rect.move(padding, text_y)
            screen.blit(turn_obj, turn_str_loc)
            text_loc = move_log_rect.move(7 * MOVE_LOG_WIDTH // 24, text_y)
        else:
            text_loc = move_log_rect.move(5 * MOVE_LOG_WIDTH // 8, text_y)
        screen.blit(text_obj, text_loc)
        if i % 2 == 1:
            text_y += (text_obj.get_height() + line_spacing)

#animation:
def animate_click_move(move, screen, position, clock):
    global board_colors, active_sq_colors
    d_row = move.end_row - move.start_row
    d_col = move.end_col - move.start_col
    frame_count = FPS // 8
    if move.is_castle: #prepare to draw the castling rook
        if move.end_col == 6: #short castle
            rook = position[move.start_row][move.end_col - 1]
            rook_start_col = move.end_col + 1
            rook_end_col = move.end_col - 1
        else: #long castle
            rook = position[move.start_row][move.end_col + 1]
            rook_start_col = move.end_col - 2
            rook_end_col = move.end_col + 1
        d_rook_col = rook_end_col - rook_start_col

    for frame in range(frame_count + 1):
        r, c = (move.start_row + d_row * frame / frame_count, move.start_col + d_col * frame / frame_count)
        if move.is_castle:
            rook_r, rook_c =(move.start_row, rook_start_col + d_rook_col * frame / frame_count)
        draw_board(screen)
        draw_pieces(screen, position)
        last_move = move
        #mask the moving piece(s)
        pg.draw.rect(screen, active_sq_colors[(last_move.start_col + last_move.start_row) % 2], pg.Rect(last_move.start_col*SQUARE_SIZE, last_move.start_row*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
        pg.draw.rect(screen, active_sq_colors[(last_move.end_col + last_move.end_row) % 2], pg.Rect(last_move.end_col*SQUARE_SIZE, last_move.end_row*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
        if move.is_castle:
            pg.draw.rect(screen, board_colors[(move.start_row + rook_end_col) % 2], pg.Rect(rook_end_col * SQUARE_SIZE, move.start_row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
        end_sq = pg.Rect(move.end_col * SQUARE_SIZE, move.end_row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
        #draw the caped piece
        if move.piece_caped != '--' and not move.is_en_passant:
            screen.blit(IMAGES[move.piece_caped], end_sq)
        #draw the moving piece(s)
        screen.blit(IMAGES[move.piece_move],pg.Rect(c * SQUARE_SIZE, r * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
        if move.is_castle:
            screen.blit(IMAGES[rook], pg.Rect(rook_c * SQUARE_SIZE, rook_r * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
        pg.display.flip()
        clock.tick(FPS)

def animate_drag_move(move, screen, position, clock):
    if move.is_castle: #prepare to draw the castling rook
        global board_colors, active_sq_colors
        frame_count = FPS // 8
        if move.end_col == 6: #short castle
            rook = position[move.start_row][move.end_col - 1]
            rook_start_col = move.end_col + 1
            rook_end_col = move.end_col - 1
        else: #long castle
            rook = position[move.start_row][move.end_col + 1]
            rook_start_col = move.end_col - 2
            rook_end_col = move.end_col + 1
        d_rook_col = rook_end_col - rook_start_col
        for frame in range(frame_count + 1):    
            draw_board(screen)
            draw_pieces(screen, position)
            rook_r, rook_c =(move.start_row, rook_start_col + d_rook_col * frame / frame_count)
            pg.draw.rect(screen, board_colors[(move.start_row + rook_end_col) % 2], pg.Rect(rook_end_col * SQUARE_SIZE, move.start_row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
            screen.blit(IMAGES[rook], pg.Rect(rook_c * SQUARE_SIZE, rook_r * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
            pg.display.flip()
            clock.tick(FPS)

def display_promotion_UI(screen, promotion_move, clock, drag_animation):
    global active_sq_colors
    start_r = promotion_move.start_row
    start_c = promotion_move.start_col
    end_r = promotion_move.end_row
    end_c = promotion_move.end_col
    arrange = 1 if end_r == 0 else -1
    promotion_pieces = ['Q', 'R', 'B', 'N']
    ally_color = promotion_move.piece_move[0]
    pieces_list = []
    #mask the moving pawn if dragging
    if drag_animation:
        pg.draw.rect(screen, active_sq_colors[(start_r + start_c) % 2], pg.Rect(start_c*SQUARE_SIZE, start_r*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
    #draw the promotion window and generate pieces
    for i in range(4):
        pg.draw.rect(screen, pg.Color("gray"), pg.Rect(end_c*SQUARE_SIZE, (end_r + i * arrange)*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
        pieces_list.append(PhysicalPiece(ally_color + promotion_pieces[i], (end_c + 0.5) * SQUARE_SIZE, (end_r + DRAG_POS + i * arrange) * SQUARE_SIZE, -3, 0, 0, 1, SQUARE_SIZE, GRAVITY, FRICTION, DRAG_POS, IMAGES))
    
    promoting = True
    selected_piece = '?'
    while promoting:
        for e in pg.event.get():
            if e.type == pg.QUIT:
                pg.quit()
            if e.type == pg.MOUSEBUTTONDOWN:
                if e.button == 3:
                    return '?'
                if e.button == 1:
                    click_point = pg.mouse.get_pos()
                    click_col = click_point[0] // SQUARE_SIZE
                    click_row = click_point[1] // SQUARE_SIZE 
                    promoting = False
        for i in range(4):
            pg.draw.rect(screen, pg.Color("silver"), pg.Rect(end_c*SQUARE_SIZE, (end_r + i * arrange)*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
        for piece in pieces_list:
            piece.update(piece.dp_x_pos, piece.dp_y_pos, 0, 0)
            piece.draw(screen)
        pg.display.flip()
        clock.tick(FPS)
    if click_col == end_c and abs(click_row - end_r) <= 3:
        selected_piece = ally_color + promotion_pieces[(click_row - end_r) * arrange]
    else:
        selected_piece = '?'
    return selected_piece

#generate and display the effect of dragging a physical piece
def dragging_physical_piece(screen, gp, legal_moves, cur_sq, move_log_font, mouse_loc, clock):
    type = gp.position[cur_sq[0]][cur_sq[1]]
    dragged_piece = PhysicalPiece(type, mouse_loc[0], mouse_loc[1], 0, 0, 0, 0, SQUARE_SIZE, GRAVITY, FRICTION, DRAG_POS, IMAGES)
    dragging = True
    drag_point_trajectory = []
    while dragging:
        for e in pg.event.get():
            if e.type == pg.MOUSEBUTTONUP:
                dragging = False
        draw_game_position(screen, gp, legal_moves, cur_sq, move_log_font)
        pg.draw.rect(screen, active_sq_colors[(cur_sq[1] + cur_sq[0]) % 2], pg.Rect(cur_sq[1]*SQUARE_SIZE, cur_sq[0]*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
        drag_point = pg.mouse.get_pos()
        drag_point_trajectory.append(drag_point)
        if len(drag_point_trajectory) >= 11:
            drag_point_trajectory.pop(0)
        drag_point_x_acc, drag_point_y_acc = cal_drag_point_acc(drag_point_trajectory)
        dragged_piece.update(drag_point[0], drag_point[1], drag_point_x_acc, drag_point_y_acc)
        dragged_piece.draw(screen)
        pg.display.flip()
        clock.tick(FPS)
    return pg.mouse.get_pos()

def cal_drag_point_acc(drag_point_trajectory):
    x_acc = 0
    y_acc = 0
    if len(drag_point_trajectory) == 10:
        x_acc = ((drag_point_trajectory[9][0] - drag_point_trajectory[5][0]) - (drag_point_trajectory[4][0] - drag_point_trajectory[0][0])) / 4 / 5
        y_acc = ((drag_point_trajectory[9][1] - drag_point_trajectory[5][1]) - (drag_point_trajectory[4][1] - drag_point_trajectory[0][1])) / 4 / 5
    return x_acc, y_acc
    
#play sound effects
def play_sound_effects(move):
    SOUND_EFFECT["move"].play()
    if move.is_cap:
        SOUND_EFFECT["capture"].play()
    if move.is_check:
        SOUND_EFFECT["check"].play()
    if move.is_castle:
        SOUND_EFFECT["castle"].play()

if __name__ == "__main__":
    main()