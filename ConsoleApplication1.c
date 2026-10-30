#include <stdio.h>
#include <stdlib.h>
#include <conio.h>
#include <string.h>

#define ROW_STRIDE 100

int g_rows = 1;
int g_player_y = 1;
int g_player_x = 1;
char g_map[100][ROW_STRIDE];
int g_level;

void init_level1(char map[][ROW_STRIDE], int *rows, int *player_y, int *player_x);
void init_level2(char map[][ROW_STRIDE], int *rows, int *player_y, int *player_x);
void init_level0(char map[][ROW_STRIDE], int *rows, int *player_y, int *player_x);
void handle_input(char map[][ROW_STRIDE], int *player_y, int *player_x);
void move_and_push(char map[][ROW_STRIDE], int old_y, int new_y, int old_x, int new_x);
void move_player(char map[][ROW_STRIDE], int *player_y, int new_y, int *player_x, int new_x);
void draw_map(char map[][ROW_STRIDE], int rows);
int count_remaining_boxes(char map[][ROW_STRIDE]);

void init_level1(char map[][ROW_STRIDE], int *rows, int *player_y, int *player_x)
{
    char tpl[100][ROW_STRIDE] = {
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
    int i;

    *rows = 11;
    *player_y = 5;
    *player_x = 6;

    for (i = 0; i < *rows; i++) {
        strcpy(map[i], tpl[i]);
    }
}

void init_level2(char map[][ROW_STRIDE], int *rows, int *player_y, int *player_x)
{
    char tpl[100][ROW_STRIDE] = {
        "012345678901",
        "1########## ",
        "2##     ### ",
        "3##O###   # ",
        "4# S O  O # ",
        "5# **# O ## ",
        "6##**#   ## ",
        "7########## ",
        "   level 2  ",
        "            ",
        "      ",
    };
    int i;

    *rows = 10;
    *player_y = 4;
    *player_x = 3;

    for (i = 0; i < *rows; i++) {
        strcpy(map[i], tpl[i]);
    }
}

void init_level0(char map[][ROW_STRIDE], int *rows, int *player_y, int *player_x)
{
    char tpl[100][ROW_STRIDE] = {
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
    int i;

    *rows = 11;
    *player_y = 5;
    *player_x = 8;

    for (i = 0; i < *rows; i++) {
        strcpy(map[i], tpl[i]);
    }
}

void handle_input(char map[][ROW_STRIDE], int *player_y, int *player_x)
{
    char ch = _getch();
    int new_y = *player_y;
    int new_x = *player_x;
    int beyond_y;
    int beyond_x;

    switch (ch) {
    case 'w': new_y--; break;
    case 'a': new_x--; break;
    case 's': new_y++; break;
    case 'd': new_x++; break;
    }

    beyond_y = new_y + new_y - *player_y;
    beyond_x = new_x + new_x - *player_x;

    if (map[new_y][new_x] != '#') {
        if (map[new_y][new_x] == ' ' || map[new_y][new_x] == '*') {
            move_player(map, player_y, new_y, player_x, new_x);
        } else if ((map[new_y][new_x] == 'O' || map[new_y][new_x] == '@')
            && (map[beyond_y][beyond_x] == ' ' || map[beyond_y][beyond_x] == '*')) {
            move_and_push(map, new_y, beyond_y, new_x, beyond_x);
            move_player(map, player_y, new_y, player_x, new_x);
        }
    }
}

void move_and_push(char map[][ROW_STRIDE], int old_y, int new_y, int old_x, int new_x)
{
    if (map[old_y][old_x] == 'O') {
        map[old_y][old_x] = ' ';
    } else {
        map[old_y][old_x] = '*';
    }

    if (map[new_y][new_x] == ' ') {
        map[new_y][new_x] = 'O';
    } else {
        map[new_y][new_x] = '@';
    }
}

void move_player(char map[][ROW_STRIDE], int *player_y, int new_y, int *player_x, int new_x)
{
    if (map[*player_y][*player_x] == 'S') {
        map[*player_y][*player_x] = ' ';
    } else {
        map[*player_y][*player_x] = '*';
    }

    if (map[new_y][new_x] == ' ') {
        map[new_y][new_x] = 'S';
    } else {
        map[new_y][new_x] = 'A';
    }

    *player_y = new_y;
    *player_x = new_x;
}

void draw_map(char map[][ROW_STRIDE], int rows)
{
    int i;

    for (i = 0; i < rows; i++) {
        puts(map[i]);
    }
}

int count_remaining_boxes(char map[][ROW_STRIDE])
{
    int count = 0;
    int i;
    int j;

    for (i = 0; i < 100; i++) {
        for (j = 0; j < 100; j++) {
            if (map[i][j] == 'O') {
                count++;
            }
        }
    }

    return count;
}

int main()
{
    while (g_level < 3) {
        if (g_level == 1) {
            init_level1(g_map, &g_rows, &g_player_y, &g_player_x);
        }
        if (g_level == 2) {
            init_level2(g_map, &g_rows, &g_player_y, &g_player_x);
        }
        if (g_level == 0) {
            init_level0(g_map, &g_rows, &g_player_y, &g_player_x);
        }

        printf("人的坐标 ： %d %d \n\n", g_player_y, g_player_x);
        draw_map(g_map, g_rows);
        printf("\n 未归位箱子还有 %d 个 \n", count_remaining_boxes(g_map));

        while (1) {
            handle_input(g_map, &g_player_y, &g_player_x);

            system("cls");

            printf("人的坐标 ： %d %d \n\n", g_player_y, g_player_x);
            draw_map(g_map, g_rows);
            printf("\n 未归位箱子还有 %d 个 \n", count_remaining_boxes(g_map));

            if (count_remaining_boxes(g_map) == 0) {
                g_level++;
                printf("\n\n 完成！ 按 enter 进入下一关 \n");
                getchar();
                system("cls");
                break;
            }
        }
    }

    system("cls");
    printf("你已经玩了3关了");
    system("pause");

    return 0;
}
