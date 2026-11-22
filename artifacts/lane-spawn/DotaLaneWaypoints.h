// DotaLaneWaypoints.h — DotA 6.83d six-lane spawn + waypoint data for creep-block AI
// Source: War3Script war3map_9.j (Rect / CreateUnit / O2 init), war3map_3.j (SPO / SSO / enter-region)
// Generated for analysis: dota-lane-spawn-waypoints (2026-11-21). Data only — do not edit hooker here.
// Coordinates are world float (WC3). Rect centers = (min+max)/2 from Rect(...) literals.

#pragma once

#ifndef DOTA_LANE_WAYPOINTS_H
#define DOTA_LANE_WAYPOINTS_H

#ifdef __cplusplus
extern "C" {
#endif

enum DotaLaneSide {
    DOTA_SIDE_RADIANT = 0, /* BO[0] Sentinel */
    DOTA_SIDE_DIRE    = 1  /* CO[0] Scourge */
};

enum DotaLaneId {
    DOTA_LANE_TOP = 0,
    DOTA_LANE_MID = 1,
    DOTA_LANE_BOT = 2
};

/* Ability I2 ('A06G') level set by SSO → indexes O2[] attack target */
enum DotaLaneAbilityLevel {
    DOTA_O2_ANCIENT_RADIANT = 1, /* II = GetUnitLoc(CZ) */
    DOTA_O2_TOP             = 2, /* CI = GetUnitLoc(BZ) */
    DOTA_O2_MID             = 3, /* BI = GetUnitLoc(ZZ) */
    DOTA_O2_BOT             = 4, /* DI = GetUnitLoc(DZ) */
    DOTA_O2_ANCIENT_DIRE    = 5  /* U0 = GetUnitLoc(OZ) */
};

typedef struct DotaVec2 {
    float x;
    float y;
} DotaVec2;

typedef struct DotaRectBox {
    float minX, minY, maxX, maxY;
    float cx, cy; /* center */
} DotaRectBox;

typedef struct DotaWaypoint {
    float x;
    float y;
    const char *name;   /* rect / building / O2 symbol */
    const char *source; /* short provenance */
} DotaWaypoint;

enum {
    DOTA_LANE_WP_MAX = 8
};

typedef struct DotaLaneSpawnWaypoints {
    const char *name;           /* e.g. "radiant_top" */
    int side;                   /* DotaLaneSide */
    int lane;                   /* DotaLaneId */
    int o2Level;                /* SSO level → O2[level] */

    /* Spawn locations = GetRectCenter(rect) assigned in war3map_9.j ~L11588 */
    DotaRectBox meleeRect;      /* NI melee (+ siege uses ranged rect) */
    DotaRectBox rangedRect;     /* SI ranged + siege */
    const char *meleeRectName;
    const char *rangedRectName;
    const char *meleeLocName;   /* B1 / O1 / A1 / RI / TI / PI */
    const char *rangedLocName;  /* E1 / C1 / D1 / I1 / QI / UI */

    /* Own T1 tower world pos (CreateUnit e00S/u00M in war3map_9.j) */
    DotaVec2 t1;
    const char *t1UnitName;

    /* Far-side attack target O2[lane] before ancient redirect */
    DotaVec2 o2Target;
    const char *o2Name;         /* CI / BI / DI */

    /* Polyline for lane projection: spawn → handoff → T2? → T1 → O2 → ancient.
       t1Index = index of own T1 in waypoints[]. */
    int waypointCount;
    int t1Index;
    DotaWaypoint waypoints[DOTA_LANE_WP_MAX];

    /* Recommended wait spot for block AI (along corridor, ~350 past melee spawn toward T1) */
    DotaVec2 waitSpot;
} DotaLaneSpawnWaypoints;

/* O2 ancient endpoints (war3map_9.j L11577–L11587, CreateUnit L10856–L10860) */
static const DotaVec2 kDotaO2_II = { -5467.9f, -5891.1f }; /* CZ e008 Radiant ancient marker */
static const DotaVec2 kDotaO2_U0 = {  4901.8f,  4536.6f }; /* OZ e001 Dire ancient marker */
static const DotaVec2 kDotaO2_CI = { -6005.1f,  5458.6f }; /* BZ e00D top destination */
static const DotaVec2 kDotaO2_BI = {  -561.7f,  -651.7f }; /* ZZ e00B mid destination */
static const DotaVec2 kDotaO2_DI = {  5901.5f, -6198.9f }; /* DZ e00A bot destination */

#define DOTA_RECT_BOX(minx, miny, maxx, maxy) \
    { (minx), (miny), (maxx), (maxy), ((minx)+(maxx))*0.5f, ((miny)+(maxy))*0.5f }

/* Six lanes: radiant top/mid/bot, dire top/mid/bot */
static const DotaLaneSpawnWaypoints kDotaLanes[6] = {
    /* ---------- 0 Radiant Top ---------- */
    {
        "radiant_top", DOTA_SIDE_RADIANT, DOTA_LANE_TOP, DOTA_O2_TOP,
        DOTA_RECT_BOX(-6336.f, -4224.f, -5984.f, -3904.f), /* B4 → B1 */
        DOTA_RECT_BOX(-6304.f, -4384.f, -6080.f, -4224.f), /* R3 → E1 */
        "B4", "R3", "B1", "E1",
        { -6112.f, 1568.f }, "HV/e00S",
        { -6005.1f, 5458.6f }, "CI/BZ",
        6, 3,
        {
            { -6160.f, -4064.f, "B1/B4", "war3map_9.j Rect B4 center" },
            { -6304.f, -3696.f, "TA", "enter-region re-issue CI (S8O)" },
            { -6112.f, -1248.f, "ZV/T2", "CreateUnit e00S -6112,-1248" },
            { -6112.f,  1568.f, "HV/T1", "CreateUnit e00S -6112,1568" },
            { -6005.1f, 5458.6f, "CI/BZ", "O2[2] GetUnitLoc(BZ)" },
            {  4901.8f, 4536.6f, "U0/OZ", "CL2/NUO → O2[5] ancient" },
        },
        { -6140.f, -3710.f } /* ~350 along toward T1 from B1 */
    },
    /* ---------- 1 Radiant Mid ---------- */
    {
        "radiant_mid", DOTA_SIDE_RADIANT, DOTA_LANE_MID, DOTA_O2_MID,
        DOTA_RECT_BOX(-4896.f, -5504.f, -4608.f, -5184.f), /* C4 → O1 */
        DOTA_RECT_BOX(-4928.f, -5760.f, -4736.f, -5536.f), /* P3 → C1 */
        "C4", "P3", "O1", "C1",
        { -1504.f, -1824.f }, "GV/e00S",
        { -561.7f, -651.7f }, "BI/ZZ",
        5, 2,
        {
            { -4752.f, -5344.f, "O1/C4", "war3map_9.j Rect C4 center" },
            { -4256.f, -4656.f, "SA", "enter-region re-issue BI (S3O)" },
            { -1504.f, -1824.f, "GV/T1", "CreateUnit e00S -1504,-1824" },
            {  -561.7f, -651.7f, "BI/ZZ", "O2[3] GetUnitLoc(ZZ)" },
            {  4901.8f, 4536.6f, "U0/OZ", "CL2/NUO → O2[5]" },
        },
        { -4550.f, -5080.f }
    },
    /* ---------- 2 Radiant Bot ---------- */
    {
        "radiant_bot", DOTA_SIDE_RADIANT, DOTA_LANE_BOT, DOTA_O2_BOT,
        DOTA_RECT_BOX(-3648.f, -6880.f, -3424.f, -6688.f), /* A4 → A1 */
        DOTA_RECT_BOX(-4224.f, -6848.f, -3968.f, -6592.f), /* T3 → D1 */
        "A4", "T3", "A1", "D1",
        { 4960.f, -6752.f }, "EV/e00S",
        { 5901.5f, -6198.9f }, "DI/DZ",
        6, 3,
        {
            { -3536.f, -6784.f, "A1/A4", "war3map_9.j Rect A4 center" },
            { -3200.f, -6768.f, "NA", "enter-region re-issue DI (SCO)" },
            {  -544.f, -6688.f, "FV/T2", "CreateUnit e00S -544,-6688" },
            {  4960.f, -6752.f, "EV/T1", "CreateUnit e00S 4960,-6752" },
            {  5901.5f, -6198.9f, "DI/DZ", "O2[4] GetUnitLoc(DZ)" },
            {  4901.8f, 4536.6f, "U0/OZ", "CL2/NUO → O2[5]" },
        },
        { -3180.f, -6775.f }
    },
    /* ---------- 3 Dire Top (Dire's top = north lane) ---------- */
    {
        "dire_top", DOTA_SIDE_DIRE, DOTA_LANE_TOP, DOTA_O2_TOP,
        DOTA_RECT_BOX(2304.f, 5280.f, 2752.f, 5728.f), /* N3 → RI */
        DOTA_RECT_BOX(2752.f, 5408.f, 3040.f, 5632.f), /* I4 → I1 */
        "N3", "I4", "RI", "I1",
        { -4704.f, 5920.f }, "GZ/u00M",
        { -6005.1f, 5458.6f }, "CI/BZ",
        6, 3,
        {
            {  2528.f, 5504.f, "RI/N3", "war3map_9.j Rect N3 center" },
            {  2464.f, 6096.f, "LA", "enter-region re-issue CI (SAO)" },
            {    32.f, 5920.f, "SZ/T2", "CreateUnit u00D 32,5920" },
            { -4704.f, 5920.f, "GZ/T1", "CreateUnit u00M -4704,5920" },
            { -6005.1f, 5458.6f, "CI/BZ", "O2[2]" },
            { -5467.9f, -5891.1f, "II/CZ", "CL2/NUO → O2[1]" },
        },
        {  2400.f, 5750.f }
    },
    /* ---------- 4 Dire Mid ---------- */
    {
        "dire_mid", DOTA_SIDE_DIRE, DOTA_LANE_MID, DOTA_O2_MID,
        DOTA_RECT_BOX(3616.f, 3584.f, 3872.f, 3872.f), /* M3 → TI */
        DOTA_RECT_BOX(4128.f, 3776.f, 4352.f, 4032.f), /* U3 → QI */
        "M3", "U3", "TI", "QI",
        { 1056.f, -96.f }, "MX/u00M",
        { -561.7f, -651.7f }, "BI/ZZ",
        5, 2,
        {
            {  3744.f, 3728.f, "TI/M3", "war3map_9.j Rect M3 center" },
            {  4032.f, 3120.f, "KA", "enter-region re-issue BI (S6O)" },
            {  1056.f,  -96.f, "MX/T1", "CreateUnit u00M 1056,-96" },
            {  -561.7f, -651.7f, "BI/ZZ", "O2[3]" },
            { -5467.9f, -5891.1f, "II/CZ", "CL2/NUO → O2[1]" },
        },
        {  3850.f, 3480.f }
    },
    /* ---------- 5 Dire Bot ---------- */
    {
        "dire_bot", DOTA_SIDE_DIRE, DOTA_LANE_BOT, DOTA_O2_BOT,
        DOTA_RECT_BOX(6176.f, 3136.f, 6400.f, 3392.f), /* L3 → PI */
        DOTA_RECT_BOX(6048.f, 3424.f, 6304.f, 3776.f), /* Q3 → UI */
        "L3", "Q3", "PI", "UI",
        { 6240.f, -2080.f }, "YZ/u00M",
        { 5901.5f, -6198.9f }, "DI/DZ",
        6, 3,
        {
            {  6288.f, 3264.f, "PI/L3", "war3map_9.j Rect L3 center" },
            {  6432.f, 2128.f, "MA", "enter-region re-issue DI (SEO)" },
            {  6304.f,  -96.f, "XZ/T2", "CreateUnit u00D 6304,-96" },
            {  6240.f, -2080.f, "YZ/T1", "CreateUnit u00M 6240,-2080" },
            {  5901.5f, -6198.9f, "DI/DZ", "O2[4]" },
            { -5467.9f, -5891.1f, "II/CZ", "CL2/NUO → O2[1]" },
        },
        {  6320.f, 2910.f }
    },
};

#undef DOTA_RECT_BOX

/* Unit type FourCC (normal / super) — SPO war3map_3.j */
enum {
    DOTA_UNIT_esen = 0x6573656EU, /* radiant melee */
    DOTA_UNIT_edry = 0x65647279U, /* radiant ranged */
    DOTA_UNIT_ebal = 0x6562616CU, /* radiant siege */
    DOTA_UNIT_e00V = 0x65303056U, /* radiant super melee */
    DOTA_UNIT_e00W = 0x65303057U, /* radiant super ranged */
    DOTA_UNIT_e026 = 0x65303236U, /* radiant super siege */
    DOTA_UNIT_ugho = 0x7567686FU, /* dire melee */
    DOTA_UNIT_unec = 0x756E6563U, /* dire ranged */
    DOTA_UNIT_umtw = 0x756D7477U, /* dire siege */
    DOTA_UNIT_u001 = 0x75303031U, /* dire super melee */
    DOTA_UNIT_u002 = 0x75303032U, /* dire super ranged */
    DOTA_UNIT_u00R = 0x75303052U  /* dire super siege */
};

/* Timing (GameStart = countdown remaining 0 in IU2, war3map_3.j ~L6824) */
enum {
    DOTA_WAVE_INTERVAL_SEC     = 30,
    DOTA_HORN_BEFORE_START_SEC = 12, /* BQO < 12 → PlaySoundBJ horn; first wave at r==0 */
    DOTA_SIEGE_EVERY_N_WAVES   = 7,  /* ModuloInteger(GetTriggerExecCount(ZG),7)==0 */
    DOTA_MELEE_PLUS_AT_SEC_1   = 999,
    DOTA_MELEE_PLUS_AT_SEC_2   = 1999,
    DOTA_MELEE_PLUS_AT_SEC_3   = 2999,
    DOTA_RANGED_PLUS_AT_SEC    = 2699,
    DOTA_CREEP_UPGRADE_PERIOD  = 450  /* UG → TQO */
};

static const int kDotaLaneCount = 6;

#ifdef __cplusplus
}
#endif

#endif /* DOTA_LANE_WAYPOINTS_H */
