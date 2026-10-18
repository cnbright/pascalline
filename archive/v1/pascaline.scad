/*
  PASCALINE V1 — TWO-DIGIT ENGINEERING PROTOTYPE
  Units: mm. Positive wheel rotation is counterclockwise viewed from above.
  This is a simplified cam / ratchet study, not an historical sautoir replica.
  Cam displacement is prescribed; printed pawl flexibility is NOT simulated.
  A rendered pose is NOT a demonstration of working contact or printability.
  Only two digits are supported here. Cascaded 3–6 digit carries need redesign.

  Export: openscad -D 'part="base"' -o base.stl pascaline.scad
  All individual parts have their bottom at Z=0.
*/
// @export base 1
// @export digit_wheel 2
// @export units_cam 1
// @export carry_slider 1
// @export drive_pawl 1
// @export stop_pawl 2
// @export shaft_spacer 2
// @export top_cover 1

part = "assembly"; // assembly, exploded, print, or one of the export identifiers
units_angle = 0;
tens_angle = 0;
show_cover = false;
show_hardware = true;
$fn = 72;

pitch = 84;
base_width = 188;
base_depth = 104;
base_thickness = 5;
shaft_clearance_d = 4.4;
wheel_radius = 35;
ratchet_root_r = 11.5;
ratchet_tip_r = 16;
ratchet_thickness = 4;
wheel_z = 12;
cam_z = 6;
cam_thickness = 4;
cam_base_r = 22;
follower_r = 1.5;
pawl_contact_r = 12.5;
carry_stroke = pawl_contact_r * tan(36); // 9.0818 mm; rigid point-contact ideal
cam_samples = 720;
slider_z = 6;
pawl_z = 12;
cover_z = 24.5;
guide_x = [28,48]; // first guide plate clears the cam's full 31.1 mm radial sweep
guide_y = -34 - carry_stroke/2;
stop_rotation = -18; // flank at 252 degrees, an integer multiple of 36
stop_anchor_x = -35; // support remains outside the rotating cam's 31.1 mm sweep
cam_pin_positions = [[-7,0],[5,5]]; // asymmetric: prevents a 180-degree phase error

function wrap(a) = (a % 360 + 360) % 360;
function ease(t) = t*t*(3-2*t);
// 9->0 is the working stroke; 0->1 returns the slider. At 0 it is HIGH.
function cam_lift(a) = let(p=wrap(a))
  p <= 36 ? carry_stroke*(1-ease(p/36)) :
  p >= 324 ? carry_stroke*ease((p-324)/36) : 0;
// Derivative of lift per radian of input rotation.
function lift_derivative(a) = let(p=wrap(a), b=36*PI/180)
  p < 36 ? -carry_stroke*6*(p/36)*(1-p/36)/b :
  p > 324 ? carry_stroke*6*((p-324)/36)*(1-(p-324)/36)/b : 0;
// Roller-center pitch curve, offset inward along its exact normal.
// The molded round follower slides rather than rolling; friction is unvalidated.
function cam_point(theta) = let(
  phase=wrap(270-theta),
  r=cam_base_r+follower_r+cam_lift(phase),
  rp=-lift_derivative(phase),
  n=[cos(theta),sin(theta)],
  t=[-sin(theta),cos(theta)],
  normal=(r*n-rp*t)/sqrt(r*r+rp*rp)
) r*n-follower_r*normal;
function rot2(p,a) = [p[0]*cos(a)-p[1]*sin(a),p[0]*sin(a)+p[1]*cos(a)];

module rounded_rect(w,h,r=3) {
  hull() for(x=[-w/2+r,w/2-r],y=[-h/2+r,h/2-r])
    translate([x,y]) circle(r=r);
}

module base() {
  difference() {
    union() {
      translate([pitch/2,0,0]) linear_extrude(base_thickness)
        rounded_rect(base_width,base_depth,5);
      // Raised anchors place the fixed flexible stop pawls beside the ratchets.
      for(x=[0,pitch]) translate([x,0,base_thickness]) rotate([0,0,stop_rotation])
        translate([stop_anchor_x,-20,0]) linear_extrude(pawl_z-base_thickness)
          rounded_rect(12,10,2);
      for(x=guide_x) translate([x,guide_y,base_thickness]) cylinder(r=1.7,h=4.8);
      // Rubber-band / extension-spring anchor; the other peg belongs to the slider.
      translate([61,36,base_thickness]) cylinder(r=2.4,h=6);
      for(x=[-44,pitch+44],y=[-44,44])
        translate([x,y,base_thickness]) cylinder(r=4.2,h=cover_z-base_thickness);
    }
    for(x=[0,pitch]) {
      translate([x,0,-.1]) cylinder(d=shaft_clearance_d,h=base_thickness+.2);
      translate([x,0,-.1]) cylinder(d=8.6,h=3.1); // optional button-head bolt recess
      for(dx=[stop_anchor_x-3,stop_anchor_x+3]) translate([x,0,0]) rotate([0,0,stop_rotation])
        translate([dx,-20,base_thickness-1]) cylinder(d=1.8,h=12);
    }
    for(x=guide_x) translate([x,guide_y,1]) cylinder(d=1.5,h=12);
    for(x=[-44,pitch+44],y=[-44,44])
      translate([x,y,cover_z-10]) cylinder(d=2.5,h=11);
    translate([pitch/2,-47,base_thickness-.6]) linear_extrude(.7)
      text("PROTOTYPE - 2 DIGIT",size=4,halign="center",valign="center");
  }
}

module ratchet_profile() {
  // Positive-rotation working flank is radial. The following side is the return ramp.
  polygon([for(k=[0:9]) each [
    [ratchet_root_r*cos(36*k),ratchet_root_r*sin(36*k)],
    [ratchet_tip_r*cos(36*k),ratchet_tip_r*sin(36*k)],
    [ratchet_root_r*cos(36*(k+1)-1),ratchet_root_r*sin(36*(k+1)-1)]
  ]]);
}

module digit_wheel() {
  difference() {
    union() {
      linear_extrude(ratchet_thickness) ratchet_profile();
      cylinder(r=9,h=8);
      translate([0,0,7]) cylinder(r=wheel_radius,h=4);
    }
    translate([0,0,-.1]) cylinder(d=shaft_clearance_d,h=11.2);
    // Blind sockets stay within the full ratchet disc; do not thin the narrower hub above.
    for(p=cam_pin_positions) translate([p[0],p[1],-.1]) cylinder(d=3.8,h=3.7);
    for(k=[0:9]) {
      a=90-36*k;
      translate([23*cos(a),23*sin(a),6.9]) cylinder(d=5.5,h=4.2);
      translate([29.3*cos(a),29.3*sin(a),10.25]) rotate([0,0,a-90])
        linear_extrude(.85) text(str(k),size=4.5,halign="center",valign="center");
    }
  }
}

module digit_wheel_print() {
  // The broad dial face rests on the bed; ratchet and hub build upward.
  translate([0,0,11]) rotate([180,0,0]) digit_wheel();
}

module units_cam() {
  difference() {
    union() {
      linear_extrude(cam_thickness)
        polygon([for(i=[0:cam_samples-1]) cam_point(i*360/cam_samples)]);
      for(p=cam_pin_positions) {
        translate([p[0],p[1],cam_thickness-.1]) cylinder(d=5.3,h=1.8);
        translate([p[0],p[1],cam_thickness-.1]) cylinder(d=3.4,h=5.1);
      }
    }
    // Sleeve passes through the cam; two pins transfer torque from the digit wheel.
    translate([0,0,-.1]) cylinder(d=8.6,h=cam_thickness+.2);
    translate([0,15,cam_thickness-.5]) linear_extrude(.6)
      text("U",size=4,halign="center",valign="center");
  }
}

module guide_slot() {
  hull() for(y=[-34-(carry_stroke+.8)/2,-34+(carry_stroke+.8)/2])
    translate([0,y]) circle(r=2.2);
}

module carry_slider() {
  difference() {
    union() {
      // Lower carrier is outside the maximum cam envelope.
      translate([-3,-40,0]) cube([73,4,3]);
      translate([64,-40,0]) cube([6,66,3]);
      translate([-follower_r,-40,0]) cube([2*follower_r,40-cam_base_r-follower_r,4]);
      translate([0,-cam_base_r-follower_r,0]) cylinder(r=follower_r,h=4);
      for(x=guide_x) translate([x,-34,0]) linear_extrude(3) rounded_rect(11,18,2);
      translate([63,18,0]) cube([8,8,6]); // separate flat-printed drive pawl seats here
      translate([58,21,0]) cube([9,5,3]);
      translate([61,24,3]) cylinder(r=2.4,h=3);
    }
    for(x=guide_x) translate([x,0,-.1]) linear_extrude(3.2) guide_slot();
    for(y=[20,24]) translate([67,y,-.1]) cylinder(d=1.8,h=6.2);
  }
}

module drive_pawl() {
  // PETG / nylon trial part. Nominal 1.2 mm leaf; actual elastic behavior must be tested.
  // Nose front edge y=0 drives the flank. On return the ramp must flex it outward (-X).
  difference() {
    union() {
      translate([63,18,0]) cube([8,8,3]);
      translate([66.3,0,0]) cube([1.2,19,3]);
      translate([66.3,0,0]) cube([pitch-pawl_contact_r-66.3,2,3]);
    }
    for(y=[20,24]) translate([67,y,-.1]) cylinder(d=2.4,h=3.2);
  }
}

module stop_pawl() {
  // Two screws fix the anchor. The long leaf deflects radially outward on forward input.
  difference() {
    union() {
      translate([stop_anchor_x,-20,0]) linear_extrude(3) rounded_rect(12,10,2);
      translate([stop_anchor_x,-20.6,0]) cube([-1-stop_anchor_x,1.2,3]);
      translate([-2,-20.6,0]) cube([2,20.6-pawl_contact_r,3]);
    }
    for(x=[stop_anchor_x-3,stop_anchor_x+3]) translate([x,-20,-.1]) cylinder(d=2.4,h=3.2);
  }
}

module shaft_spacer() {
  difference() {
    union() {
      cylinder(d=12,h=1); // cam rests on this flange, one mm above the base
      cylinder(d=8,h=7); // digit wheel rests here, at assembly Z=12
    }
    translate([0,0,-.1]) cylinder(d=shaft_clearance_d,h=7.2);
  }
}

module top_cover() {
  difference() {
    translate([pitch/2,0,0]) linear_extrude(3) rounded_rect(base_width,base_depth,5);
    for(x=[0,pitch]) translate([x,0,-.1]) cylinder(r=34,h=3.2);
    for(x=[-44,pitch+44],y=[-44,44]) translate([x,y,-.1]) cylinder(d=3.4,h=3.2);
    translate([pitch/2,-44,2.35]) linear_extrude(.75)
      text("PASCALINE  /  PROTOTYPE",size=4,halign="center",valign="center");
  }
  for(x=[0,pitch]) translate([x,0,0]) linear_extrude(3)
    polygon([[-3,36],[3,36],[0,32]]);
  for(x=[0,pitch]) translate([x,43,3]) linear_extrude(.4)
    text(x==0?"UNITS":"TENS",size=3.5,halign="center",valign="center");
}

module hardware() {
  color([.6,.63,.67]) for(x=[0,pitch]) translate([x,0,1]) cylinder(d=4,h=28);
  // Return spring is schematic: a straight strand between the two pegs.
  color([.9,.4,.08]) hull() {
    translate([61,36,10]) sphere(r=.7,$fn=16);
    translate([61,24-cam_lift(units_angle),10]) sphere(r=.7,$fn=16);
  }
}

module assembly(explode=0) {
  color([.22,.28,.32]) base();
  for(x=[0,pitch]) color([.65,.68,.71])
    translate([x,0,5+explode*.25]) shaft_spacer();
  color([.87,.59,.13]) translate([0,0,cam_z+explode*.4]) rotate([0,0,units_angle]) units_cam();
  color([.15,.55,.61]) translate([0,-cam_lift(units_angle),slider_z+explode*.4]) carry_slider();
  color([.96,.67,.19]) translate([0,-cam_lift(units_angle),pawl_z+explode*.75]) drive_pawl();
  for(x=[0,pitch]) color([.95,.51,.17]) translate([x,0,pawl_z+explode*.75])
    rotate([0,0,stop_rotation]) stop_pawl();
  for(x=[0,pitch]) color(x==0?[.84,.87,.86]:[.9,.79,.55])
    translate([x,0,wheel_z+explode]) rotate([0,0,x==0?units_angle:tens_angle]) digit_wheel();
  if(show_cover) color([.22,.28,.32,.8]) translate([0,0,cover_z+explode*1.5]) top_cover();
  if(show_hardware && explode==0) hardware();
}

module print_layout() {
  // A layout for inspection. Fits neither every printer nor every material workflow.
  translate([52,52,0]) base();
  translate([42,150,0]) digit_wheel_print();
  translate([120,150,0]) digit_wheel_print();
  translate([195,150,0]) units_cam();
  translate([240,48,0]) carry_slider();
  translate([178,200,0]) drive_pawl();
  translate([270,130,0]) stop_pawl();
  translate([270,150,0]) stop_pawl();
  translate([245,180,0]) shaft_spacer();
  translate([260,180,0]) shaft_spacer();
  translate([52,254,0]) top_cover();
}

if(part=="assembly") assembly();
else if(part=="exploded") assembly(30);
else if(part=="print") print_layout();
else if(part=="base") base();
else if(part=="digit_wheel") digit_wheel_print();
else if(part=="units_cam") units_cam();
else if(part=="carry_slider") carry_slider();
else if(part=="drive_pawl") drive_pawl();
else if(part=="stop_pawl") stop_pawl();
else if(part=="shaft_spacer") shaft_spacer();
else if(part=="top_cover") top_cover();
else assert(false,str("Unknown part: ",part));
