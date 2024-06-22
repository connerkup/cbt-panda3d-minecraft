from math import pi, sin, cos
from direct.showbase.ShowBase import ShowBase
from panda3d.core import loadPrcFile
from panda3d.core import DirectionalLight, AmbientLight
from panda3d.core import TransparencyAttrib
from panda3d.core import WindowProperties
from panda3d.core import CollisionTraverser, CollisionNode, CollisionBox, CollisionRay, CollisionHandlerQueue, CollisionSphere, CollisionHandlerPusher, BitMask32
from panda3d.core import GeomNode  # Import for debugging collision nodes
from direct.gui.OnscreenImage import OnscreenImage
from direct.task import Task
from panda3d.core import ClockObject

# Initialize globalClock
globalClock = ClockObject.getGlobalClock()

loadPrcFile('settings.prc')

def degToRad(degrees):
    return degrees * (pi / 180.0)

class MyGame(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        self.selectedBlockType = 'grass'
        self.isJumping = False
        self.isCrouching = False
        self.jumpSpeed = 15
        self.gravity = -30
        self.zVelocity = 0
        self.onGround = False

        self.loadModels()
        self.setupLights()
        self.generateTerrain()
        self.setupCamera()
        self.setupSkybox()
        
        self.cameraSwingActivated = False
        self.lastMouseX = 0
        self.lastMouseY = 0
        
        self.captureMouse()
        self.setupControls()

        self.taskMgr.add(self.update, 'update')
        self.taskMgr.add(self.fixedUpdate, 'fixedUpdate')

        self.cTrav = CollisionTraverser()
        self.rayQueue = CollisionHandlerQueue()
        self.pusher = CollisionHandlerPusher()
        self.setupCollision()

    def setupCollision(self):
        ray = CollisionRay()
        ray.setFromLens(self.camNode, (0, 0))
        rayNode = CollisionNode('line-of-sight')
        rayNode.addSolid(ray)
        rayNode.setIntoCollideMask(BitMask32.bit(1))
        rayNodePath = self.camera.attachNewNode(rayNode)
        self.cTrav.addCollider(rayNodePath, self.rayQueue)

        playerCollider = CollisionSphere(0, 0, 0, 1)
        playerNode = CollisionNode('player')
        playerNode.addSolid(playerCollider)
        playerNode.setFromCollideMask(BitMask32.bit(0))
        playerNode.setIntoCollideMask(BitMask32.allOff())
        playerNodePath = self.camera.attachNewNode(playerNode)
        self.pusher.addCollider(playerNodePath, self.camera)
        self.cTrav.addCollider(playerNodePath, self.pusher)
        self.pusher.add_in_pattern('%fn-into-%in')
        self.accept('player-into-block-collision-node', self.onCollision)

    def onCollision(self, entry):
        into_normal = entry.getSurfaceNormal(entry.getIntoNodePath())
        if into_normal.z > 0.7:  # Ground collision
            self.isJumping = False
            self.zVelocity = 0
            self.onGround = True
            # Adjust the camera to be slightly above the ground to avoid getting stuck
            self.camera.setZ(entry.getSurfacePoint(entry.getIntoNodePath()).getZ() + 0.1)
        elif into_normal.z < -0.7:  # Ceiling collision
            self.zVelocity = 0
        else:  # Wall collision
            # Adjust the position to avoid getting stuck inside walls
            displacement = entry.getSurfaceNormal(entry.getIntoNodePath()) * 0.1
            self.camera.setPos(self.camera.getPos() - displacement)

    def fixedUpdate(self, task):
        fixed_dt = 1 / 60
        self.updateMovement(fixed_dt)
        return task.again

    def update(self, task):
        dt = globalClock.getDt()
        self.updateCameraSwing()
        return task.cont

    def updateMovement(self, dt):
        playerMoveSpeed = 10

        x_movement = 0
        y_movement = 0

        if self.keyMap['forward']:
            x_movement -= dt * playerMoveSpeed * sin(degToRad(self.camera.getH()))
            y_movement += dt * playerMoveSpeed * cos(degToRad(self.camera.getH()))
        if self.keyMap['backward']:
            x_movement += dt * playerMoveSpeed * sin(degToRad(self.camera.getH()))
            y_movement -= dt * playerMoveSpeed * cos(degToRad(self.camera.getH()))
        if self.keyMap['left']:
            x_movement -= dt * playerMoveSpeed * cos(degToRad(self.camera.getH()))
            y_movement -= dt * playerMoveSpeed * sin(degToRad(self.camera.getH()))
        if self.keyMap['right']:
            x_movement += dt * playerMoveSpeed * cos(degToRad(self.camera.getH()))
            y_movement += dt * playerMoveSpeed * sin(degToRad(self.camera.getH()))

        newPos = self.camera.getPos() + (x_movement, y_movement, 0)
        self.camera.setPos(newPos)

        if not self.onGround:
            self.zVelocity += self.gravity * dt
        else:
            self.zVelocity = 0

        self.zVelocity = max(self.zVelocity, -50)

        newZPos = self.camera.getZ() + self.zVelocity * dt
        self.camera.setZ(newZPos)

        if self.camera.getZ() < -100:
            self.camera.setPos(0, 0, 3)
            self.zVelocity = 0

        if self.keyMap['jump'] and self.onGround:
            self.isJumping = True
            self.onGround = False
            self.zVelocity = self.jumpSpeed

        if self.keyMap['crouch']:
            if not self.isCrouching:
                self.camera.setZ(self.camera.getZ() - 0.5)
                self.isCrouching = True
        else:
            if self.isCrouching:
                self.camera.setZ(self.camera.getZ() + 0.5)
                self.isCrouching = False

    def updateCameraSwing(self):
        if self.cameraSwingActivated:
            md = self.win.getPointer(0)
            mouseX = md.getX()
            mouseY = md.getY()
            windowCenterX = self.win.getXSize() // 2
            windowCenterY = self.win.getYSize() // 2

            mouseChangeX = mouseX - windowCenterX
            mouseChangeY = mouseY - windowCenterY

            self.cameraSwingFactor = 0.1

            currentH = self.camera.getH()
            currentP = self.camera.getP()

            self.camera.setHpr(
                currentH - mouseChangeX * self.cameraSwingFactor,
                min(90, max(-90, currentP - mouseChangeY * self.cameraSwingFactor)),
                0
            )

            self.win.movePointer(0, windowCenterX, windowCenterY)

    def setupControls(self):
        self.keyMap = {
            "forward": False,
            "backward": False,
            "left": False,
            "right": False,
            "jump": False,
            "crouch": False,
        }

        self.accept('escape', self.releaseMouse)
        self.accept('mouse1', self.handleLeftClick)
        self.accept('mouse3', self.placeBlock)

        self.accept('w', self.updateKeyMap, ['forward', True])
        self.accept('w-up', self.updateKeyMap, ['forward', False])
        self.accept('a', self.updateKeyMap, ['left', True])
        self.accept('a-up', self.updateKeyMap, ['left', False])
        self.accept('s', self.updateKeyMap, ['backward', True])
        self.accept('s-up', self.updateKeyMap, ['backward', False])
        self.accept('d', self.updateKeyMap, ['right', True])
        self.accept('d-up', self.updateKeyMap, ['right', False])
        self.accept('space', self.updateKeyMap, ['jump', True])
        self.accept('space-up', self.updateKeyMap, ['jump', False])
        self.accept('lcontrol', self.updateKeyMap, ['crouch', True])
        self.accept('lcontrol-up', self.updateKeyMap, ['crouch', False])

        self.accept('1', self.setSelectedBlockType, ['grass'])
        self.accept('2', self.setSelectedBlockType, ['dirt'])
        self.accept('3', self.setSelectedBlockType, ['sand'])
        self.accept('4', self.setSelectedBlockType, ['stone'])
    
    def setSelectedBlockType(self, type):
        self.selectedBlockType = type
    
    def handleLeftClick(self):
        self.captureMouse()
        self.removeBlock()

    def removeBlock(self):
        if self.rayQueue.getNumEntries() > 0:
            self.rayQueue.sortEntries()
            rayHit = self.rayQueue.getEntry(0)

            hitNodePath = rayHit.getIntoNodePath()
            hitObject = hitNodePath.getPythonTag('owner')
            if hitObject:
                distanceFromPlayer = hitObject.getDistance(self.camera)
                if distanceFromPlayer < 12:
                    hitNodePath.clearPythonTag('owner')
                    hitObject.removeNode()

    def placeBlock(self):
        if self.rayQueue.getNumEntries() > 0:
            self.rayQueue.sortEntries()
            rayHit = self.rayQueue.getEntry(0)
            hitNodePath = rayHit.getIntoNodePath()
            normal = rayHit.getSurfaceNormal(hitNodePath)
            hitObject = hitNodePath.getPythonTag('owner')
            if hitObject:
                distanceFromPlayer = hitObject.getDistance(self.camera)
                if distanceFromPlayer < 14:
                    hitBlockPos = hitObject.getPos()
                    newBlockPos = hitBlockPos + normal * 2
                    self.createNewBlock(newBlockPos.x, newBlockPos.y, newBlockPos.z, self.selectedBlockType)
    
    def updateKeyMap(self, key, value):
        self.keyMap[key] = value

    def captureMouse(self):
        self.cameraSwingActivated = True

        md = self.win.getPointer(0)
        self.lastMouseX = md.getX()
        self.lastMouseY = md.getY()

        properties = WindowProperties()
        properties.setCursorHidden(True)
        properties.setMouseMode(WindowProperties.M_absolute)
        self.win.requestProperties(properties)

        windowCenterX = self.win.getXSize() // 2
        windowCenterY = self.win.getYSize() // 2
        self.win.movePointer(0, windowCenterX, windowCenterY)

    def releaseMouse(self):
        self.cameraSwingActivated = False

        properties = WindowProperties()
        properties.setCursorHidden(False)
        properties.setMouseMode(WindowProperties.M_absolute)
        self.win.requestProperties(properties)

    def setupCamera(self):
        self.disableMouse()
        self.camera.setPos(0, 0, 3)
        self.camLens.setFov(80)

        crosshairs = OnscreenImage(
            image='crosshairs.png',
            pos=(0, 0, 0),
            scale=0.05,
        )
        crosshairs.setTransparency(TransparencyAttrib.MAlpha)

    def setupSkybox(self):
        skybox = self.loader.loadModel('skybox/skybox.egg')
        skybox.setScale(500)
        skybox.setBin('background', 1)
        skybox.setDepthWrite(0)
        skybox.setLightOff()
        skybox.reparentTo(self.render)
    
    def generateTerrain(self):
        for z in range(10):
            for y in range(20):
                for x in range(20):
                    self.createNewBlock(
                        x * 2 - 20,
                        y * 2 - 20,
                        -z * 2,
                        'grass' if z == 0 else 'dirt'
                    )

    def createNewBlock(self, x, y, z, type):
        newBlockNode = self.render.attachNewNode('new-block-placeholder')
        newBlockNode.setPos(x, y, z)

        if type == 'grass':
            self.grassBlock.instanceTo(newBlockNode)
        elif type == 'dirt':
            self.dirtBlock.instanceTo(newBlockNode)
        elif type == 'sand':
            self.sandBlock.instanceTo(newBlockNode)
        elif type == 'stone':
            self.stoneBlock.instanceTo(newBlockNode)

        blockSolid = CollisionBox((-1, -1, -1), (1, 1, 1))
        blockNode = CollisionNode('block-collision-node')
        blockNode.addSolid(blockSolid)
        blockNode.setIntoCollideMask(BitMask32.bit(0))
        collider = newBlockNode.attachNewNode(blockNode)
        collider.setPythonTag('owner', newBlockNode)

    def loadModels(self):
        self.grassBlock = self.loader.loadModel('grass-block.glb')
        self.dirtBlock = self.loader.loadModel('dirt-block.glb')
        self.stoneBlock = self.loader.loadModel('stone-block.glb')
        self.sandBlock = self.loader.loadModel('sand-block.glb')

    def setupLights(self):
        mainLight = DirectionalLight('main light')
        mainLightNodePath = self.render.attachNewNode(mainLight)
        mainLightNodePath.setHpr(30, -60, 0)
        self.render.setLight(mainLightNodePath)

        ambientLight = AmbientLight('ambient light')
        ambientLight.setColor((0.3, 0.3, 0.3, 1))
        ambientLightNodePath = self.render.attachNewNode(ambientLight)
        self.render.setLight(ambientLightNodePath)
    
game = MyGame()
game.run()
