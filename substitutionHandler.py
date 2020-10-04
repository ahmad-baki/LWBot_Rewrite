

def getCourseRoles(ctx):
    kurse = []
    # all course roles except the @everyone role
    for r in ctx.guild.roles[1:len(ctx.guild.roles)]:
        if "Kurse" in r.name:
            break
        kurse.append(r)
    return kurse

def getCourseRoleNames(ctx):
    return [c.name for c in getCourseRoles(ctx)]

async def createCourseRole(ctx, name):
    await ctx.guild.create_role(name=name)