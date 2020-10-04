import lwConfig

def getMyCourseRoles(ctxAuthor):
    kurse = []
    # all course roles except the @everyone role
    for r in ctxAuthor.roles[1:len(ctxAuthor.roles)]:
        if not "Kurse" in r.name:
            kurse.append(r)
        else:
            break
    return kurse


def getMyCourseRoleNames(ctx):
    return [c.name for c in getMyCourseRoles(ctx)]


async def createCourseRole(ctx, name):
    await ctx.guild.create_role(name=name)
