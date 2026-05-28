#include <stdio.h>
#include <stdlib.h>
#include <conio.h>
#include <string.h>
#include <windows.h>

#define ROW_STRIDE 100

char g_map[100][ROW_STRIDE];
int g_rows;
int g_player_x;
int g_player_y;
int g_level;

static const char* g_level0_tpl[] = {
    "01234567890123456789",
    "1###################",
    "2#                 #",
    "3#     *           #",
    "4#                 #",
    "5#     OS O *      #",
    "6#                 #",
    "7#                 #",
    "8#                 #",
    "9###################",
    "#      demo        #",
};

static const char* g_level1_tpl[] = {
    "0123456789",
    "1    ###     ",
    "2    #*#     ",
    "3    # #     ",
    "4 ####O######",
    "5 #* OS O * #",
    "6 #####O#####",
    "7     # #    ",
    "8     #*#    ",
    "9     ###    ",
    "   level 1   ",
};

static const char* g_level2_tpl[] = {
    "012345678901",
    "1########## ",
    "2##     ### ",
    "3##O###   # ",
    "4# S O  O # ",
    "5# **# O ## ",
    "6##**#   ## ",
    "7########## ",
    "   level 2  ",
    "",
};

void init_level(const char* tpl[], int rows, int start_y, int start_x)
{
    for (int i = 0; i < rows; i++) {
        strcpy_s(g_map[i], ROW_STRIDE, tpl[i]);
    }
    for (int i = rows; i < 100; i++) {
        g_map[i][0] = 0;
    }
    g_rows = rows;
    g_player_y = start_y;
    g_player_x = start_x;
}

void draw_map()
{
    for (int i = 0; i < g_rows; i++) {
        puts(g_map[i]);
    }
}

int count_remaining_boxes()
{
    int count = 0;
    for (int i = 0; i < 100; i++) {
        for (int j = 0; j < 100; j++) {
            if (g_map[i][j] == 'O') {
                count++;
            }
        }
    }
    return count;
}

void move_and_push(int old_y, int new_y, int old_x, int new_x)
{
    if (g_map[old_y][old_x] == 'O') {
        g_map[old_y][old_x] = ' ';
    } else {
        g_map[old_y][old_x] = '*';
    }

    if (g_map[new_y][new_x] == ' ') {
        g_map[new_y][new_x] = 'O';
    } else {
        g_map[new_y][new_x] = '@';
    }
}

void move_player(int old_y, int new_y, int old_x, int new_x)
{
    if (g_map[g_player_y][g_player_x] == 'S') {
        g_map[g_player_y][g_player_x] = ' ';
    } else {
        g_map[g_player_y][g_player_x] = '*';
    }

    if (g_map[new_y][new_x] == ' ') {
        g_map[new_y][new_x] = 'S';
    } else {
        g_map[new_y][new_x] = 'A';
    }

    g_player_y = new_y;
    g_player_x = new_x;
}

void handle_input()
{
    int new_y = g_player_y;
    int new_x = g_player_x;
    int ch = _getch();

    switch (ch) {
    case 'a': new_x--; break;
    case 'd': new_x++; break;
    case 'w': new_y--; break;
    case 's': new_y++; break;
    default: return;
    }

    int beyond_y = new_y + (new_y - g_player_y);
    int beyond_x = new_x + (new_x - g_player_x);

    char target = g_map[new_y][new_x];

    if (target == '#') {
        return;
    }

    if (target == ' ' || target == '*') {
        move_player(g_player_y, new_y, g_player_x, new_x);
        return;
    }

    if (target == 'O' || target == '@') {
        char beyond = g_map[beyond_y][beyond_x];
        if (beyond == ' ' || beyond == '*') {
            move_and_push(new_y, beyond_y, new_x, beyond_x);
            move_player(g_player_y, new_y, g_player_x, new_x);
        }
    }
}

int main()
{
    g_level = 0;

    while (g_level < 3) {
        if (g_level == 0) {
            init_level(g_level0_tpl, 11, 5, 8);
        } else if (g_level == 1) {
            init_level(g_level1_tpl, 11, 5, 6);
        } else if (g_level == 2) {
            init_level(g_level2_tpl, 10, 4, 3);
        }

        printf("\n \xc8\xcb\xb5\xc4\xd7\xf8\xb1\xea \xa3\xba %d %d \n\n", g_player_y, g_player_x);
        draw_map();
        printf("\n \xce\xb4\xb9\xe9\xce\xbb\xcf\xe4\xd7\xd3\xbb\xb9\xd3\xd0 %d \xb8\xf6 \n", count_remaining_boxes());

        while (1) {
            handle_input();

            system("cls");

            printf("\n \xc8\xcb\xb5\xc4\xd7\xf8\xb1\xea \xa3\xba %d %d \n\n", g_player_y, g_player_x);
            draw_map();
            printf("\n \xce\xb4\xb9\xe9\xce\xbb\xcf\xe4\xd7\xd3\xbb\xb9\xd3\xd0 %d \xb8\xf6 \n", count_remaining_boxes());

            if (count_remaining_boxes() == 0) {
                g_level++;
                printf("\n\n \xcd\xea\xb3\xc9\xa3\xa1 \xb0\xb4 enter \xbd\xf8\xc8\xeb\xcf\xc2\xd2\xbb\xb9\xd8 \n");
                system("pause");
                system("cls");
                break;
            }
        }
    }

    system("cls");
    printf("\n \xc4\xe3\xd2\xd1\xbe\xad\xcd\xe6\xc1\xcb" "3\xb9\xd8\xc1\xcb \n");
    system("pause");
    return 0;
}
