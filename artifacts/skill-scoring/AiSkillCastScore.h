// Lightweight pure-logic skill cast scoring (offline-replayable).
// Intended drop-in for War3Launcher/hooker — no JASS natives.
#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <string>
#include <vector>

namespace ai_skill_score {

enum class DamageType : uint8_t { Magical, Physical, Pure, Unknown };
enum class GeometryKind : uint8_t {
    None,
    UnitTarget,
    PointCircle,
    PointCircleDelayed,
    ForwardCircle,   // SF raze
    ShockwaveCone,   // Lina Dragon Slave
    RadialLines,     // SF Requiem
    SelfAoe,
    AttrScaledUnit   // Morph Adaptive Strike
};

enum class ScoringClass : uint8_t {
    Passive,
    NukeUnit,
    DirectionalAoe,
    DirectionalWave,
    DelayedPointAoe,
    TeamfightAoeLines,
    AttrScaledUnit,
    PointAoe,
    SelfAoe,
    Generic,
    UtilityNoDamage
};

struct LevelFloats {
    float v[4];
    int n = 0;
    float at(int level1based) const {
        if (n <= 0) return 0.f;
        const int i = std::clamp(level1based, 1, n) - 1;
        return v[i];
    }
};

struct SkillFormula {
    char code[5]{};
    GeometryKind geom = GeometryKind::None;
    ScoringClass klass = ScoringClass::Generic;
    DamageType dmgType = DamageType::Unknown;
    LevelFloats damage;
    LevelFloats mana;
    LevelFloats cool;
    LevelFloats range;
    float radius = 0.f;
    float centerDist = 0.f;   // ForwardCircle
    float delay = 0.f;        // PointCircleDelayed
    float length = 0.f;       // Shockwave
    float endRadius = 0.f;
    float castPoint = 0.67f;
    float turnToleranceDeg = 9.f;
    bool emptyCastBlock = true;
    bool utilityIgnoreEmpty = false; // scout / escape / vision
    // RadialLines
    float dmgPerLine[3]{};
    int dmgPerLineN = 0;
};

struct Vec2 { float x = 0, y = 0; };

struct UnitSnap {
    Vec2 pos;
    Vec2 vel;          // world units / second
    float hp = 0;
    float armor = 0;
    float magicResist = 0.25f; // total MR in [0,1)
    float keyWeight = 1.f;     // w_key from teamfight scorer
    bool isHero = false;
    bool spellImmune = false;
};

struct CasterSnap {
    Vec2 pos;
    float facingDeg = 0;
    float mana = 0;
    float castPoint = 0.67f;
    float agi = 0, str = 0; // Morph etc.
    int souls = 0;          // SF Necromastery
};

struct CastIntent {
    const SkillFormula* skill = nullptr;
    int level = 1;
    float castFacingDeg = 0; // for directional
    Vec2 point{};            // for point AOE
    const UnitSnap* unitTarget = nullptr;
    bool denyWaiting = false;
    bool farmContext = false;
};

struct CastScoreResult {
    float score = 0;          // 0..100
    float hitProb = 0;
    float expectedDmg = 0;
    float theoreticalMax = 0;
    int hitCount = 0;
    bool block = false;
    const char* reason = "";
};

inline float armorMult(float armor) {
    // DefenseArmor k=0.06
    return 1.f / (1.f + 0.06f * armor);
}

inline float magicTaken(float raw, float totalMr) {
    return raw * (1.f - std::clamp(totalMr, 0.f, 0.99f));
}

inline float postMitigation(float raw, DamageType t, const UnitSnap& e) {
    if (t == DamageType::Pure) return raw;
    if (t == DamageType::Physical) return raw * armorMult(e.armor);
    if (t == DamageType::Magical) return magicTaken(raw, e.magicResist);
    return raw;
}

inline float angGapDeg(float a, float b) {
    float d = std::fmod(std::fabs(a - b), 360.f);
    return d > 180.f ? 360.f - d : d;
}

inline Vec2 predict(const UnitSnap& u, float dt) {
    return {u.pos.x + u.vel.x * dt, u.pos.y + u.vel.y * dt};
}

inline float dist2(Vec2 a, Vec2 b) {
    const float dx = a.x - b.x, dy = a.y - b.y;
    return dx * dx + dy * dy;
}

// --- Damage evaluators (subset; table-driven extension via SkillFormula) ---

inline float morphAdaptiveDamage(const SkillFormula& s, int level, float agi, float str) {
    const float base = 20.f * float(level);
    const float agiRatio = (str > 0.f) ? (agi / str) : 99.f;
    float mult;
    if (agiRatio < 0.5f) mult = 0.25f;
    else if (agiRatio > 1.5f) mult = 0.5f * float(level);
    else mult = 0.25f + (agiRatio - 0.5f) * (0.5f * float(level) - 0.25f);
    return base + mult * agi;
}

inline CastScoreResult scoreForwardCircle(
    const CastIntent& in, const CasterSnap& caster, const std::vector<UnitSnap>& enemies)
{
    CastScoreResult r;
    const SkillFormula& s = *in.skill;
    const float dt = caster.castPoint + 0.08f;
    const float facing = in.castFacingDeg;
    const float rad = facing * 0.01745329252f;
    const Vec2 center{
        caster.pos.x + s.centerDist * std::cos(rad),
        caster.pos.y + s.centerDist * std::sin(rad)};
    const float raw = s.damage.at(in.level);
    r.theoreticalMax = raw;
    const float ang = angGapDeg(caster.facingDeg, facing);
    float expected = 0.f;
    int kills = 0;
    for (const auto& e : enemies) {
        if (e.spellImmune && s.dmgType == DamageType::Magical) continue;
        const Vec2 p = predict(e, dt);
        if (dist2(p, center) > s.radius * s.radius) continue;
        const float dmg = postMitigation(raw, s.dmgType, e);
        expected += dmg * e.keyWeight;
        ++r.hitCount;
        if (e.hp <= dmg) ++kills;
    }
    if (r.hitCount == 0) {
        r.score = 0;
        r.hitProb = 0;
        r.block = s.emptyCastBlock && !s.utilityIgnoreEmpty;
        r.reason = "empty";
        return r;
    }
    if (ang > s.turnToleranceDeg) {
        r.score = 0;
        r.hitProb = 0;
        r.block = true;
        r.reason = "facing";
        return r;
    }
    r.hitProb = 1.f; // discrete hit model; soft edge can be added later
    r.expectedDmg = expected;
    // Farm-oriented score used by lane raze (mirrors war3hook_ai_lane.inl)
    float sc = (kills >= 2 ? 75.f : 55.f) + float(std::max(0, kills - 1)) * 15.f;
    sc -= ang * 3.5f;
    if (in.farmContext && kills == 1 && in.denyWaiting && caster.mana >= 150.f)
        sc = (std::max)(sc, 60.f); // 必漏关键兵：抬到放行阈值
    r.score = std::clamp(sc, 0.f, 100.f);
    if (in.farmContext && kills == 1 && !(in.denyWaiting && caster.mana >= 150.f)) {
        r.block = true;
        r.reason = "farm_single";
        return r;
    }
    r.block = r.score < 60.f;
    r.reason = r.block ? "low_score" : "ok";
    return r;
}

inline CastScoreResult scoreAoeWeighted(
    const CastIntent& in, const CasterSnap& caster, const std::vector<UnitSnap>& enemies, Vec2 center, float radius, float delay)
{
    CastScoreResult r;
    const SkillFormula& s = *in.skill;
    const float raw = s.damage.at(in.level);
    r.theoreticalMax = raw * std::max(1, (int)enemies.size());
    float sum = 0.f;
    for (const auto& e : enemies) {
        if (!e.isHero) continue;
        if (e.spellImmune && s.dmgType == DamageType::Magical) continue;
        const Vec2 p = predict(e, caster.castPoint + delay);
        if (dist2(p, center) > radius * radius) continue;
        const float dmg = postMitigation(raw, s.dmgType, e);
        sum += e.keyWeight * dmg;
        ++r.hitCount;
    }
    r.expectedDmg = sum;
    r.hitProb = r.hitCount > 0 ? 1.f : 0.f;
    if (r.hitCount == 0) {
        r.score = 0;
        r.block = s.emptyCastBlock && !s.utilityIgnoreEmpty;
        r.reason = "empty";
        return r;
    }
    // Caller normalizes against best candidate; here return raw benefit scaled softly.
    r.score = std::clamp(sum / std::max(1.f, raw) * 25.f, 0.f, 100.f);
    r.block = r.score < 60.f;
    r.reason = r.block ? "low_score" : "ok";
    return r;
}

inline CastScoreResult aiScoreSkillCast(
    const CastIntent& in,
    const CasterSnap& caster,
    const std::vector<UnitSnap>& enemies)
{
    CastScoreResult bad;
    bad.block = true;
    bad.reason = "no_skill";
    if (!in.skill) return bad;
    const SkillFormula& s = *in.skill;
    switch (s.geom) {
    case GeometryKind::ForwardCircle:
        return scoreForwardCircle(in, caster, enemies);
    case GeometryKind::PointCircleDelayed:
        return scoreAoeWeighted(in, caster, enemies, in.point, s.radius, s.delay);
    case GeometryKind::PointCircle:
    case GeometryKind::SelfAoe:
        return scoreAoeWeighted(in, caster, enemies,
                                s.geom == GeometryKind::SelfAoe ? caster.pos : in.point,
                                s.radius, 0.f);
    case GeometryKind::AttrScaledUnit: {
        CastScoreResult r;
        if (!in.unitTarget) { r.block = true; r.reason = "no_target"; return r; }
        const float raw = morphAdaptiveDamage(s, in.level, caster.agi, caster.str);
        r.theoreticalMax = 20.f * float(in.level) + (0.5f * float(in.level)) * caster.agi;
        r.expectedDmg = postMitigation(raw, DamageType::Magical, *in.unitTarget);
        r.hitProb = 1.f;
        r.hitCount = 1;
        r.score = std::clamp(100.f * r.expectedDmg / std::max(1.f, r.theoreticalMax), 0.f, 100.f);
        r.block = r.score < 60.f;
        r.reason = "ok";
        return r;
    }
    default:
        bad.reason = "unhandled_geom";
        return bad;
    }
}

} // namespace ai_skill_score
